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
        network=runtime.network_snapshot(); network["phone"]["model"]=runtime.phone_model or "not reported"
        perimeter=runtime.perimeter_snapshot()
        return jsonify({"service":"tracepulse","state":decision["state"],"session":{"active":bool(session),"approved":session.approved if session else False,"device_label":session.device_label if session else None,"session_id_prefix":session.session_id[:12] if session else None},"heartbeat":{"age_seconds":heartbeat.age_seconds(),"expired":heartbeat.expired(),"received_count":heartbeat.received_count},"os_session":os_state,"decision":decision,"network":network,"perimeter":{"limit_meters":perimeter["base_limit_meters"],"effective_limit_meters":perimeter["effective_limit_meters"],"perimeter_expanded":perimeter["expanded"],"perimeter_reason":perimeter["reason"],"lock_delay_seconds":runtime.config.proximity_lock_delay_seconds,"distance_meters":runtime.last_distance_meters,"rssi_dbm":runtime.last_rssi,"inside":runtime.last_distance_meters is not None and runtime.last_distance_meters<=perimeter["effective_limit_meters"]},"network_guard":runtime.last_network_guard or {"available":False,"error":"not yet checked","ml_model_state":"MODEL_NOT_READY"},"context":runtime.last_context or {"available":False,"error":"not yet checked","ml_model_state":"MODEL_NOT_READY"},"scheduler":runtime.scheduler_snapshot(),"audit":{"valid":audit.verify()}})
    except PermissionError as e:return jsonify({"error":str(e)}),403
    except Exception: current_app.logger.exception("status failed"); return jsonify({"error":"status unavailable"}),503