from flask import Blueprint,current_app,jsonify,request
import ipaddress
bp=Blueprint("status_api",__name__,url_prefix="/api/status")
def local():
    if current_app.config.get("TRACEPULSE_LOCAL_STATUS_ONLY",True):
        try: ok=ipaddress.ip_address(request.remote_addr or "").is_loopback
        except ValueError: ok=False
        if not ok: raise PermissionError("status is local-only")
@bp.get("/health")
def health(): return jsonify({"service":"tracepulse","status":"online","transport":"tls-wss-required"})
@bp.get("")
def status():
    try:
        local(); runtime=current_app.extensions["tracepulse_runtime"]; session=current_app.extensions["tracepulse_sessions"].active(); heartbeat=current_app.extensions["tracepulse_heartbeat"]; audit=current_app.extensions["tracepulse_audit"]; os_state=runtime.os_status(); decision=runtime.decision_snapshot()
        return jsonify({"service":"tracepulse","state":decision["state"],"session":{"active":bool(session),"device_label":session.device_label if session else None,"session_id_prefix":session.session_id[:12] if session else None},"heartbeat":{"age_seconds":heartbeat.age_seconds(),"expired":heartbeat.expired(),"received_count":heartbeat.received_count},"os_session":os_state,"decision":decision,"audit":{"valid":audit.verify()}})
    except PermissionError as e:return jsonify({"error":str(e)}),403
    except Exception: current_app.logger.exception("status failed"); return jsonify({"error":"status unavailable"}),503