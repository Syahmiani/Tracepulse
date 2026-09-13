from __future__ import annotations
import asyncio,secrets,time
from dataclasses import replace
from flask import Flask
from flask_socketio import SocketIO
from .config import Config
from .state_machine import SecurityStateMachine
from .decision_engine import DecisionEngine
from .socket_server import SecureSocketServer
from .security.pairing import PairingManager
from .security.sessions import SessionManager
from .security.sessions import UnlockAssertion,verify_unlock_assertion
from .security.tls import server_context
from .sensors.heartbeat import HeartbeatMonitor
from .sensors.ble_rssi import BleRssiCollector
from .ai.kalman import KalmanFilter1D
from .os_integration.kali_session import KaliSession
from .os_integration.lock_engine import LockEngine,UnlockAuthorization
from .storage.database import Database,DatabaseConfig
from .storage.audit_log import AuditLog
from .api.pairing_routes import bp as pairing_bp
from .api.status_routes import bp as status_bp
from .api.calibration_routes import bp as calibration_bp
class Services:
    def __init__(self,app,config):
        self.app=app; self.config=config; self.db=Database(DatabaseConfig(config.database_path)); self.db.open(); self.db.initialize(); self.db.connection.execute("UPDATE sessions SET status='expired' WHERE status='active'"); self.audit=AuditLog(self.db); self.pairing=PairingManager(); self.sessions=SessionManager(); self.heartbeat=HeartbeatMonitor(config.heartbeat_timeout_seconds); self.os=KaliSession(); self.lock_engine=LockEngine(self.os); self.machine=SecurityStateMachine(); self.filter=KalmanFilter1D(); self.last_ble=None; self.last_rssi=None; self.unlock_nonces={}; self.decision=DecisionEngine(state_machine=self.machine,lock_callback=self.lock_now,heartbeat_timeout_seconds=config.heartbeat_timeout_seconds,ble_max_age_seconds=config.ble_max_age_seconds,rssi_threshold_dbm=config.rssi_threshold_dbm)
    def lock_now(self,*,reason):
        result=self.lock_engine.lock_now(reason=reason); self.audit.append(severity="critical",category="lock",event_type="lock_result",reason=reason,evidence={"confirmed":result.confirmed,"latency_ms":result.dispatch_latency_ms}); return result
    def handle_message(self,session,event,payload,sequence):
        if event=="heartbeat": self.heartbeat.record(sequence=sequence,payload_size_bytes=len(str(payload).encode())); return [{"event":"heartbeat_ack","payload":{"received_at_ms":int(time.time()*1000)}}]
        if event=="lock_request":
            d=self.decision.evaluate(session_active=True,heartbeat_age=self.heartbeat.age_seconds(),ble_age=None if self.last_ble is None else time.monotonic()-self.last_ble,filtered_rssi_dbm=self.last_rssi,os_locked=self.os.inspect().locked_hint is True,extra_reasons=(str(payload.get("reason","manual lock")),)); result=self.decision.apply(d); return [{"event":"lock_result","payload":dict(result.__dict__) if result else dict(confirmed=False)}]
        if event=="unlock_challenge_request": self.unlock_nonces[session.session_id]=secrets.token_urlsafe(24); return [{"event":"unlock_challenge","payload":dict(nonce=self.unlock_nonces[session.session_id],expires_at_epoch=time.time()+30)}]
        if event=="unlock_request":
            assertion=UnlockAssertion.from_mapping(payload.get("assertion",{})); nonce=self.unlock_nonces.pop(session.session_id,None)
            if nonce is None or not verify_unlock_assertion(assertion,session_id=session.session_id,expected_nonce=nonce,public_key=session.device_signing_public_key): raise PermissionError("device authorization failed")
            result=self.lock_engine.unlock_authorized(authorization=UnlockAuthorization(assertion.verification_id,"android_biometric",assertion.issued_at_epoch,assertion.expires_at_epoch,True,"unlock_workstation")); self.audit.append(severity="high",category="unlock",event_type="unlock_result",reason="verified Android authorization",evidence={"confirmed":result.confirmed}); return [{"event":"unlock_result","payload":dict(result.__dict__)}]
        raise ValueError("unsupported event")
    def os_status(self):
        try: info=self.os.inspect(); return {"available":True,"locked_hint":info.locked_hint,"type":info.session_type,"active":info.active}
        except Exception as exc:return {"available":False,"state":"unknown","error":str(exc)}
    def decision_snapshot(self):
        d=self.decision.last; return {"state":self.machine.state.value,"reason":d.reason if d else "not evaluated","model_state":d.model_state if d else "MODEL_NOT_READY"}
    def watchdog(self):
        while True:
            try:
                if self.sessions.active():
                    d=self.decision.evaluate(session_active=True,heartbeat_age=self.heartbeat.age_seconds(),ble_age=None if self.last_ble is None else time.monotonic()-self.last_ble,filtered_rssi_dbm=self.last_rssi,os_locked=self.os_status().get("locked_hint") is True)
                    if d.should_lock:self.decision.apply(d)
            except Exception:self.app.logger.exception("watchdog failure")
            time.sleep(.1)
    async def ble_loop(self):
        if not self.config.ble_service_uuid:return
        async for item in BleRssiCollector(service_uuid=self.config.ble_service_uuid,adapter=self.config.ble_adapter).stream(): self.last_ble=item.timestamp_monotonic; self.last_rssi=self.filter.update(item.rssi_dbm,item.timestamp_monotonic).filtered_dbm
    def start_ble(self):
        try:asyncio.run(self.ble_loop())
        except Exception:self.app.logger.exception("BLE collector degraded")
def create_app(overrides=None):
    config=Config.from_env(bool((overrides or {}).get("TESTING")))
    if overrides:
        names={"TRACEPULSE_SERVICE_URL":"service_url","TRACEPULSE_BIND_HOST":"bind_host","TRACEPULSE_PORT":"port","TRACEPULSE_DATABASE_PATH":"database_path","TRACEPULSE_TLS_CERT":"tls_cert","TRACEPULSE_TLS_KEY":"tls_key","TRACEPULSE_BLE_SERVICE_UUID":"ble_service_uuid","TRACEPULSE_BLE_ADAPTER":"ble_adapter","TRACEPULSE_HEARTBEAT_TIMEOUT_SECONDS":"heartbeat_timeout_seconds","TRACEPULSE_BLE_MAX_AGE_SECONDS":"ble_max_age_seconds","TRACEPULSE_RSSI_THRESHOLD_DBM":"rssi_threshold_dbm","TRACEPULSE_LOCAL_ADMIN_ONLY":"local_admin_only","TRACEPULSE_LOCAL_STATUS_ONLY":"local_status_only"}
        values={names[key]:value for key,value in overrides.items() if key in names}; values["testing"]=bool(overrides.get("TESTING",config.testing)); config=replace(config,**values)
    config.validate_runtime(); app=Flask(__name__); app.config.update(TRACEPULSE_CONFIG=config,TRACEPULSE_SERVICE_URL=config.service_url,TRACEPULSE_LOCAL_ADMIN_ONLY=config.local_admin_only,TRACEPULSE_LOCAL_STATUS_ONLY=config.local_status_only)
    services=Services(app,config); app.extensions.update(tracepulse_config=config,tracepulse_pairing=services.pairing,tracepulse_sessions=services.sessions,tracepulse_db=services.db,tracepulse_heartbeat=services.heartbeat,tracepulse_audit=services.audit,tracepulse_runtime=services)
    app.register_blueprint(pairing_bp); app.register_blueprint(status_bp); app.register_blueprint(calibration_bp); return app

def create_socketio(app):
    socketio=SocketIO(app,async_mode="threading",cors_allowed_origins=[],logger=False,engineio_logger=False); server=SecureSocketServer(socketio,app.extensions["tracepulse_runtime"]); server.register(); services=app.extensions["tracepulse_runtime"]; socketio.start_background_task(services.watchdog); socketio.start_background_task(services.start_ble); return socketio

def main():
    app=create_app(); socketio=create_socketio(app); config=app.config["TRACEPULSE_CONFIG"]; context=server_context(config.tls_cert,config.tls_key); socketio.run(app,host=config.bind_host,port=config.port,ssl_context=context,allow_unsafe_werkzeug=True)