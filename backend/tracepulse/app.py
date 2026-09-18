from __future__ import annotations
import asyncio,getpass,os,secrets,socket,subprocess,time,uuid
from dataclasses import replace
from datetime import datetime
from flask import Flask,make_response,request
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
from .sensors.ble_rssi_simulator import SimulatedBleRssiCollector
from .sensors.arp_guard import ArpGuard
from .sensors.network_context import NetworkContextCollector
from .ai.kalman import KalmanFilter1D,rssi_to_distance_meters
from .ai.explanations import explain_lock
from .ai.dynamic_perimeter import DynamicPerimeter
from .scheduler import ManualScheduler
from .os_integration.kali_session import KaliSession
from .os_integration.lock_engine import LockEngine,UnlockAuthorization
from .storage.database import Database,DatabaseConfig
from .storage.audit_log import AuditLog
from .api.pairing_routes import bp as pairing_bp
from .api.status_routes import bp as status_bp
from .api.calibration_routes import bp as calibration_bp
from .api.heartbeat_routes import bp as heartbeat_bp
from .api.runtime_routes import bp as runtime_bp
from .api.scheduler_routes import bp as scheduler_bp
class Services:
    def __init__(self,app,config):
        self.app=app; self.config=config; self.db=Database(DatabaseConfig(config.database_path)); self.db.open(); self.db.initialize(); self.audit=AuditLog(self.db); self.pairing=PairingManager(); self.sessions=SessionManager(); self.heartbeat=HeartbeatMonitor(config.heartbeat_timeout_seconds); self.os=KaliSession(); self.lock_engine=LockEngine(self.os); self.machine=SecurityStateMachine(); self.filter=KalmanFilter1D(); self.last_ble=None; self.last_rssi=None; self.last_rssi_covariance=None; self.last_distance_meters=None; self.phone_ip=None; self.phone_mac=None; self.phone_model=None; self.phone_last_seen=None; self.unlock_nonces={}; self.lock_enforced=False
        self.arp_guard=ArpGuard(); self.network_context_collector=NetworkContextCollector(trusted_bssids=config.trusted_bssids); self.perimeter=DynamicPerimeter(base_limit_meters=config.proximity_distance_meters,max_expansion_meters=config.dynamic_perimeter_max_expansion_meters,stability_covariance_threshold=config.dynamic_perimeter_stability_covariance); self.scheduler=ManualScheduler()
        self.last_network_guard=None; self.last_context=None; self._next_network_guard_check=0.0
        self.decision=DecisionEngine(state_machine=self.machine,lock_callback=self.lock_now,heartbeat_timeout_seconds=config.heartbeat_timeout_seconds,ble_max_age_seconds=config.ble_max_age_seconds,rssi_threshold_dbm=config.rssi_threshold_dbm,proximity_lock_delay_seconds=config.proximity_lock_delay_seconds)
    def network_snapshot(self):
        try: host_ip=socket.gethostbyname(socket.gethostname())
        except socket.error: host_ip="127.0.0.1"
        mac=":".join(f"{(uuid.getnode() >> shift) & 0xff:02x}" for shift in range(40,-1,-8))
        phone_mac=self.phone_mac
        if not phone_mac and self.phone_ip:
            try:
                neighbor=subprocess.run(["ip","neigh","show",self.phone_ip],capture_output=True,text=True,timeout=1,check=False).stdout.split()
                if "lladdr" in neighbor: phone_mac=neighbor[neighbor.index("lladdr")+1]
            except (OSError,subprocess.SubprocessError): pass
        return {"laptop":{"hostname":socket.gethostname(),"user":getpass.getuser(),"ip":host_ip,"mac":mac},"phone":{"ip":self.phone_ip or "not observed","mac":phone_mac or "not exposed","last_seen_epoch":self.phone_last_seen}}
    def lock_now(self,*,reason):
        result=self.lock_engine.lock_now(reason=reason)
        if result.confirmed:
            self.lock_enforced=True
        self.audit.append(severity="critical",category="lock",event_type="lock_result",reason=reason,evidence={"confirmed":result.confirmed,"latency_ms":result.dispatch_latency_ms}); return result
    def handle_message(self,session,event,payload,sequence):
        self.phone_ip=request.remote_addr
        self.phone_last_seen=time.time()
        if isinstance(payload,dict) and payload.get("device_mac"): self.phone_mac=str(payload["device_mac"])
        if event=="heartbeat": self.heartbeat.record(sequence=sequence,payload_size_bytes=len(str(payload).encode())); return [{"event":"heartbeat_ack","payload":{"received_at_ms":int(time.time()*1000)}}]
        if event=="lock_request":
            result=self.lock_now(reason=str(payload.get("reason","manual lock"))); return [{"event":"lock_result","payload":dict(result.__dict__)}]
        if event=="unlock_challenge_request": self.unlock_nonces[session.session_id]=secrets.token_urlsafe(24); return [{"event":"unlock_challenge","payload":dict(nonce=self.unlock_nonces[session.session_id],expires_at_epoch=time.time()+30)}]
        if event=="unlock_request":
            assertion=UnlockAssertion.from_mapping(payload.get("assertion",{})); nonce=self.unlock_nonces.pop(session.session_id,None)
            if nonce is None or not verify_unlock_assertion(assertion,session_id=session.session_id,expected_nonce=nonce,public_key=session.device_signing_public_key): raise PermissionError("device authorization failed")
            source="browser_demo" if assertion.verification_id=="browser-demo" else "android_biometric"
            self.lock_enforced=False
            result=self.lock_engine.unlock_authorized(authorization=UnlockAuthorization(assertion.verification_id,source,assertion.issued_at_epoch,assertion.expires_at_epoch,True,"unlock_workstation")); self.audit.append(severity="high",category="unlock",event_type="unlock_result",reason=f"verified {source} authorization",evidence={"confirmed":result.confirmed}); return [{"event":"unlock_result","payload":dict(result.__dict__)}]
        raise ValueError("unsupported event")
    def os_status(self):
        try: info=self.os.inspect(); return {"available":True,"locked_hint":info.locked_hint,"type":info.session_type,"active":info.active}
        except Exception as exc:return {"available":False,"state":"unknown","error":str(exc)}
    def refresh_network_guard(self):
        # Heuristic, non-ML sniff/MitM detection (gateway MAC + duplicate IP checks).
        # The trained ai/network_guard.py Isolation Forest model stays MODEL_NOT_READY
        # until real labelled packet-timing data has been collected and calibrated.
        try:
            assessment=self.arp_guard.assess()
            is_anomaly=bool(assessment["gateway_mac_changed"] or assessment["duplicate_ip_addresses"])
            self.last_network_guard={"available":True,"heuristic":"arp_gateway_check","is_anomaly":is_anomaly,"gateway_ip":assessment["gateway_ip"],"gateway_mac_changed":assessment["gateway_mac_changed"],"duplicate_ip_addresses":list(assessment["duplicate_ip_addresses"]),"ml_model_state":"MODEL_NOT_READY"}
        except Exception as exc:
            self.last_network_guard={"available":False,"error":str(exc),"ml_model_state":"MODEL_NOT_READY"}
        return self.last_network_guard
    def refresh_context(self):
        # Heuristic Wi-Fi/network context (trusted BSSID, signal, encryption).
        # The trained ai/context_knn.py classifier stays MODEL_NOT_READY until real
        # labelled context samples have been collected and calibrated.
        try:
            reading=self.network_context_collector.collect()
            self.last_context={"available":True,"ssid":reading.ssid,"wifi_is_trusted":reading.wifi_is_trusted,"wifi_is_encrypted":reading.wifi_is_encrypted,"signal_percent":reading.signal_percent,"ml_model_state":"MODEL_NOT_READY"}
        except Exception as exc:
            self.last_context={"available":False,"error":str(exc),"ml_model_state":"MODEL_NOT_READY"}
        return self.last_context
    def perimeter_snapshot(self):
        trusted=self.last_context.get("wifi_is_trusted") if self.last_context else None
        reading=self.perimeter.evaluate(rssi_covariance=self.last_rssi_covariance,network_is_trusted=trusted)
        return {"base_limit_meters":reading.base_limit_meters,"effective_limit_meters":reading.effective_limit_meters,"expanded":reading.expanded,"reason":reading.reason,"simulated":self.config.ble_simulate}
    def scheduler_snapshot(self):
        active=self.scheduler.active_at(datetime.now())
        return {"schedules":[s.as_dict() for s in self.scheduler.list()],"active_lock":active.as_dict() if active else None}
    def decision_snapshot(self):
        d = self.decision.last
        if d is None:
            return {"state": "UNPAIRED", "reason": "not evaluated", "model_state": "MODEL_NOT_READY", "explanation": None}
        explanation = explain_lock(d.reason, self.lock_enforced) if d.should_lock else None
        return {
            "state": d.state.value,
            "reason": d.reason,
            "model_state": d.model_state,
            "explanation": explanation.as_dict() if explanation else None,
        }
    def watchdog(self):
        while True:
            try:
                now_monotonic=time.monotonic()
                if now_monotonic>=self._next_network_guard_check:
                    self._next_network_guard_check=now_monotonic+self.config.network_guard_check_interval_seconds
                    self.refresh_network_guard(); self.refresh_context()
                if self.sessions.active():
                    ble_age=None if self.last_ble is None else now_monotonic-self.last_ble
                    perimeter=self.perimeter_snapshot(); effective_limit=perimeter["effective_limit_meters"]
                    extra_reasons=[]
                    if self.last_network_guard and self.last_network_guard.get("is_anomaly"): extra_reasons.append("network anomaly detected (gateway/ARP change)")
                    active_schedule=self.scheduler.active_at(datetime.now())
                    if active_schedule is not None: extra_reasons.append(f"scheduled lock window: {active_schedule.label}")
                    d=self.decision.evaluate(session_active=True,heartbeat_age=self.heartbeat.age_seconds(),ble_age=ble_age,filtered_rssi_dbm=self.last_rssi,proximity_out_of_range=ble_age is None or ble_age>self.config.ble_max_age_seconds or (self.last_distance_meters is not None and self.last_distance_meters>effective_limit),proximity_distance_meters=self.last_distance_meters,os_locked=self.os_status().get("locked_hint") is True,extra_reasons=extra_reasons)
                    if self.lock_enforced and self.os_status().get("locked_hint") is not True and not self.os.screen_locker_active():
                        self.lock_now(reason="lock hold enforcement")
            except Exception:self.app.logger.exception("watchdog failure")
            time.sleep(.1)
    async def ble_loop(self):
        if self.config.ble_simulate:
            collector=SimulatedBleRssiCollector(adapter=self.config.ble_adapter)
        elif self.config.ble_service_uuid:
            collector=BleRssiCollector(service_uuid=self.config.ble_service_uuid,adapter=self.config.ble_adapter)
        else:
            return
        async for item in collector.stream():
            estimate=self.filter.update(item.rssi_dbm,item.timestamp_monotonic)
            self.last_ble=item.timestamp_monotonic; self.last_rssi=estimate.filtered_dbm; self.last_rssi_covariance=estimate.covariance; self.last_distance_meters=rssi_to_distance_meters(self.last_rssi,self.config.proximity_reference_rssi_dbm,self.config.proximity_path_loss_exponent)
    def start_ble(self):
        try:asyncio.run(self.ble_loop())
        except Exception:self.app.logger.exception("BLE collector degraded")
def create_app(overrides=None):
    config=Config.from_env(bool((overrides or {}).get("TESTING")))
    if overrides:
        names={"TRACEPULSE_SERVICE_URL":"service_url","TRACEPULSE_BIND_HOST":"bind_host","TRACEPULSE_PORT":"port","TRACEPULSE_DATABASE_PATH":"database_path","TRACEPULSE_TLS_CERT":"tls_cert","TRACEPULSE_TLS_KEY":"tls_key","TRACEPULSE_BLE_SERVICE_UUID":"ble_service_uuid","TRACEPULSE_BLE_ADAPTER":"ble_adapter","TRACEPULSE_HEARTBEAT_TIMEOUT_SECONDS":"heartbeat_timeout_seconds","TRACEPULSE_BLE_MAX_AGE_SECONDS":"ble_max_age_seconds","TRACEPULSE_RSSI_THRESHOLD_DBM":"rssi_threshold_dbm","TRACEPULSE_PROXIMITY_DISTANCE_METERS":"proximity_distance_meters","TRACEPULSE_PROXIMITY_LOCK_DELAY_SECONDS":"proximity_lock_delay_seconds","TRACEPULSE_PROXIMITY_REFERENCE_RSSI_DBM":"proximity_reference_rssi_dbm","TRACEPULSE_PROXIMITY_PATH_LOSS_EXPONENT":"proximity_path_loss_exponent","TRACEPULSE_LOCAL_ADMIN_ONLY":"local_admin_only","TRACEPULSE_LOCAL_STATUS_ONLY":"local_status_only"}
        values={names[key]:value for key,value in overrides.items() if key in names}; values["testing"]=bool(overrides.get("TESTING",config.testing)); config=replace(config,**values)
    config.validate_runtime(); app=Flask(__name__); app.config.update(TRACEPULSE_CONFIG=config,TRACEPULSE_SERVICE_URL=config.service_url,TRACEPULSE_LOCAL_ADMIN_ONLY=config.local_admin_only,TRACEPULSE_LOCAL_STATUS_ONLY=config.local_status_only)
    frontend_origin=os.getenv("TRACEPULSE_FRONTEND_ORIGIN","*")
    @app.before_request
    def handle_preflight():
        if request.method=="OPTIONS":
            return make_response("",204)
    @app.after_request
    def add_frontend_cors(response):
        origin=request.headers.get("Origin")
        if frontend_origin=="*" or origin==frontend_origin:
            response.headers["Access-Control-Allow-Origin"]=frontend_origin if frontend_origin!="*" else "*"
            response.headers["Access-Control-Allow-Methods"]="GET,POST,OPTIONS"
            response.headers["Access-Control-Allow-Headers"]="Content-Type"
        return response
    services=Services(app,config); app.extensions.update(tracepulse_config=config,tracepulse_pairing=services.pairing,tracepulse_sessions=services.sessions,tracepulse_db=services.db,tracepulse_heartbeat=services.heartbeat,tracepulse_audit=services.audit,tracepulse_runtime=services,tracepulse_scheduler=services.scheduler)
    app.register_blueprint(pairing_bp); app.register_blueprint(status_bp); app.register_blueprint(calibration_bp); app.register_blueprint(heartbeat_bp); app.register_blueprint(runtime_bp); app.register_blueprint(scheduler_bp); return app

def create_socketio(app):
    socketio=SocketIO(app,async_mode="threading",cors_allowed_origins=os.getenv("TRACEPULSE_FRONTEND_ORIGIN","*"),logger=False,engineio_logger=False); server=SecureSocketServer(socketio,app.extensions["tracepulse_runtime"]); server.register(); services=app.extensions["tracepulse_runtime"]; socketio.start_background_task(services.watchdog); socketio.start_background_task(services.start_ble); return socketio

def main():
    app=create_app(); socketio=create_socketio(app); config=app.config["TRACEPULSE_CONFIG"]; context=server_context(config.tls_cert,config.tls_key); socketio.run(app,host=config.bind_host,port=config.port,ssl_context=context,allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()