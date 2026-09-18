from __future__ import annotations
import hashlib, ipaddress, json
from datetime import datetime, timezone
from flask import Blueprint,current_app,jsonify,request
from ..security.pairing import PairingError,PairingManager,b64,public_key_fingerprint
from ..security.sessions import SessionError,SessionManager
bp=Blueprint("pairing_api",__name__,url_prefix="/api/pairing")
def ext(name):
    value=current_app.extensions.get(name)
    if value is None: raise RuntimeError(f"missing extension: {name}")
    return value
def body():
    if not request.is_json or not isinstance(request.get_json(silent=True),dict): raise ValueError("JSON object required")
    return request.get_json()
def string(value,name,max_length=512):
    if not isinstance(value,str) or not value.strip() or len(value)>max_length: raise ValueError(f"invalid {name}")
    return value.strip()
def local_only():
    if not current_app.config.get("TRACEPULSE_LOCAL_ADMIN_ONLY",True): return
    try: address=ipaddress.ip_address(request.remote_addr or "")
    except ValueError: raise PermissionError("local request required")
    if not address.is_loopback: raise PermissionError("local request required")
def error(message,status): return jsonify({"error":message}),status
def device_id(key): return hashlib.sha256(key.encode()).hexdigest()[:32]
def pairing_options(): return {"allow_insecure_local": current_app.config["TRACEPULSE_CONFIG"].allow_insecure_local}
@bp.post("/offer")
def offer():
    try:
        local_only(); value=body() if request.data else {}; service_url=current_app.config["TRACEPULSE_SERVICE_URL"]; result=ext("tracepulse_pairing").create_offer(service_url=service_url,ttl_seconds=float(value.get("ttl_seconds",120)),**pairing_options())
        return jsonify({"handle":result.handle,"qr_payload":result.qr_payload,"expires_at_epoch":result.expires_at_epoch,"server_public_key_b64":result.server_public_key_b64}),201
    except PermissionError as e:return error(str(e),403)
    except (ValueError,PairingError) as e:return error(str(e),400)
    except RuntimeError:return error("pairing unavailable",503)

@bp.post("/prepare")
def prepare():
    try:
        local_only()
        value=body() if request.data else {}
        pairing:PairingManager=ext("tracepulse_pairing")
        sessions:SessionManager=ext("tracepulse_sessions")
        active=sessions.active()
        if active and active.status.value=="active": return error("an active pairing already exists; unpair before pairing another device",409)
        pairing.reset()
        sessions.revoke("pairing reset")
        sessions.reset()
        db=ext("tracepulse_db")
        with db.transaction() as conn:
            conn.execute("UPDATE sessions SET status='revoked',revoked_reason='pairing reset' WHERE status='active'")
        result=pairing.create_offer(service_url=current_app.config["TRACEPULSE_SERVICE_URL"],ttl_seconds=float(value.get("ttl_seconds",120)),**pairing_options())
        identity=ext("tracepulse_runtime").network_snapshot()["laptop"]
        return jsonify({"handle":result.handle,"qr_payload":result.qr_payload,"expires_at_epoch":result.expires_at_epoch,"server_public_key_b64":result.server_public_key_b64,"server_key_fingerprint":public_key_fingerprint(result.server_public_key_b64),"laptop":identity}),201
    except PermissionError as e:return error(str(e),403)
    except (ValueError,PairingError) as e:return error(str(e),400)
    except Exception:
        current_app.logger.exception("pairing preparation failed")
        return error("pairing preparation failed",503)

@bp.post("/reset")
def reset():
    try:
        ext("tracepulse_pairing").reset()
        sessions:SessionManager=ext("tracepulse_sessions")
        sessions.revoke("pairing reset")
        sessions.reset()
        db=ext("tracepulse_db")
        with db.transaction() as conn:
            conn.execute("UPDATE sessions SET status='revoked',revoked_reason='pairing reset' WHERE status='active'")
        return jsonify({"status":"reset"}),200
    except Exception as exc:
        current_app.logger.exception("pairing reset failed")
        return error("pairing reset failed",503)
@bp.post("/begin")
def begin():
    try:
        value=body(); result=ext("tracepulse_pairing").begin(handle=string(value.get("handle"),"handle",256),token=string(value.get("token"),"token")); response=dict(result.__dict__); response["server_key_fingerprint"]=public_key_fingerprint(result.server_public_key_b64); response["laptop"]=ext("tracepulse_runtime").network_snapshot()["laptop"]; return jsonify(response)
    except (ValueError,PairingError) as e:return error(str(e),400)
@bp.post("/complete")
def complete():
    try:
        value=body(); handle=string(value.get("handle"),"handle",256); token=string(value.get("token"),"token"); signing=string(value.get("device_signing_public_key_b64"),"device_signing_public_key_b64"); phone=string(value.get("phone_public_key_b64"),"phone_public_key_b64")
        result=ext("tracepulse_pairing").complete(handle=handle,token=token,challenge_b64=string(value.get("challenge_b64"),"challenge_b64"),phone_public_key_b64=phone,device_signing_public_key_b64=signing,client_confirmation_b64=string(value.get("client_confirmation_b64"),"client_confirmation_b64"))
        manager:SessionManager=ext("tracepulse_sessions"); session=manager.establish(shared_secret=result.shared_secret,device_label=string(value.get("device_label"),"device_label",128),device_signing_public_key=__import__("base64").urlsafe_b64decode(signing+"="*(-len(signing)%4)))
        runtime=ext("tracepulse_runtime"); runtime.phone_ip=request.remote_addr; runtime.phone_model=string(value.get("device_model","unknown"),"device_model",256)
        now=datetime.now(timezone.utc).isoformat(); did=device_id(phone); db=ext("tracepulse_db")
        try:
            with db.transaction() as conn:
                conn.execute("INSERT INTO paired_devices(device_id,label,public_key_b64,signing_public_key_b64,created_at_utc,last_seen_at_utc,revoked_at_utc) VALUES(?,?,?,?,?,?,NULL) ON CONFLICT(device_id) DO UPDATE SET label=excluded.label,signing_public_key_b64=excluded.signing_public_key_b64,last_seen_at_utc=excluded.last_seen_at_utc,revoked_at_utc=NULL",(did,value["device_label"],phone,signing,now,now))
                conn.execute("INSERT INTO sessions(session_id,device_id,key_salt_b64,created_at_utc,last_seen_at_utc,status) VALUES(?,?,?,?,?,'active')",(session.session_id,did,b64(session.key_salt),now,now))
        except Exception:
            manager.revoke("database persistence failed"); raise
        return jsonify({"session_id":session.session_id,"device_id":did,"session_key_salt_b64":b64(session.key_salt),"server_confirmation_b64":result.server_confirmation_b64,"status":"active"}),201
    except (ValueError,PairingError,SessionError) as e:return error(str(e),400)
    except Exception as e: current_app.logger.exception("pairing completion failed"); return error("pairing could not be completed",409)

@bp.post("/approve")
def approve():
    try:
        value=body(); session=ext("tracepulse_sessions").active()
        requested_id=value.get("session_id")
        if session is None or (requested_id is not None and session.session_id != string(requested_id,"session_id")): return error("pairing session unavailable",409)
        ext("tracepulse_sessions").approve(session.session_id)
        return jsonify({"status":"approved"}),200
    except (ValueError,SessionError) as e:return error(str(e),409)
