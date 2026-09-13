from __future__ import annotations
import ipaddress,json,re,secrets
from datetime import datetime,timezone
from flask import Blueprint,current_app,jsonify,request
bp=Blueprint("calibration_api",__name__,url_prefix="/api/calibration")
_TYPES={"ble_rssi","network","context","iat"}
def local():
    if current_app.config.get("TRACEPULSE_LOCAL_ADMIN_ONLY",True):
        try: ok=ipaddress.ip_address(request.remote_addr or "").is_loopback
        except ValueError: ok=False
        if not ok: raise PermissionError("calibration is local-only")
def now(): return datetime.now(timezone.utc).isoformat()
def db(): return current_app.extensions["tracepulse_db"]
@bp.post("/runs")
def start():
    try:
        local(); value=request.get_json(silent=True) or {}; kind=str(value.get("calibration_type","")).lower().strip()
        if kind not in _TYPES: raise ValueError("unsupported calibration type")
        run=secrets.token_urlsafe(18); stamp=now(); label=value.get("label") if isinstance(value.get("label"),str) else None
        with db().transaction() as c:c.execute("INSERT INTO calibration_runs(run_id,calibration_type,label,started_at_utc,status,metadata_json) VALUES(?,?,?,?,?,?)",(run,kind,label,stamp,"running",json.dumps(value.get("metadata",{}),sort_keys=True)))
        return jsonify({"run_id":run,"status":"running","started_at_utc":stamp}),201
    except PermissionError as e:return jsonify({"error":str(e)}),403
    except ValueError as e:return jsonify({"error":str(e)}),400
@bp.post("/runs/<run_id>/complete")
def finish(run_id):
    try:
        local(); value=request.get_json(silent=True) or {}; state=value.get("status","complete"); count=int(value.get("sample_count",0)); digest=value.get("dataset_sha256")
        if not re.fullmatch(r"[A-Za-z0-9_-]{10,128}",run_id) or state not in {"complete","failed"}: raise ValueError("invalid calibration completion")
        if state=="complete" and (count<=0 or not isinstance(digest,str) or not re.fullmatch(r"[0-9a-fA-F]{64}",digest)): raise ValueError("real sample count and dataset hash are required")
        with db().transaction() as c:
            cur=c.execute("UPDATE calibration_runs SET ended_at_utc=?,sample_count=?,dataset_sha256=?,status=?,metadata_json=? WHERE run_id=? AND status='running'",(now(),count,digest.lower() if digest else None,state,json.dumps(value.get("metadata",{}),sort_keys=True),run_id))
            if cur.rowcount!=1:return jsonify({"error":"run not found or already closed"}),404
        return jsonify({"run_id":run_id,"status":state,"sample_count":count,"dataset_sha256":digest})
    except PermissionError as e:return jsonify({"error":str(e)}),403
    except ValueError as e:return jsonify({"error":str(e)}),400