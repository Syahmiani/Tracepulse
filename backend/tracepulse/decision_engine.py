from __future__ import annotations
import time
from dataclasses import dataclass
from .state_machine import SecurityState,SecurityStateMachine
@dataclass(frozen=True)
class Decision: state:SecurityState; should_lock:bool; reason:str; model_state:str; evidence:dict
class DecisionEngine:
    def __init__(self,*,state_machine:SecurityStateMachine,lock_callback,heartbeat_timeout_seconds=2.2,ble_max_age_seconds=3.0,rssi_threshold_dbm=None,proximity_lock_delay_seconds=5.0): self.machine=state_machine; self.lock_callback=lock_callback; self.heartbeat_timeout=heartbeat_timeout_seconds; self.ble_max_age=ble_max_age_seconds; self.rssi_threshold=rssi_threshold_dbm; self.proximity_lock_delay=proximity_lock_delay_seconds; self.proximity_out_of_range_since=None; self.last=None; self.lock_in_progress=False
    def evaluate(self,*,session_active,heartbeat_age,ble_age,filtered_rssi_dbm,os_locked,proximity_out_of_range=False,proximity_distance_meters=None,extra_reasons=(),models_ready=False,now=None):
        if not session_active: d=Decision(SecurityState.UNPAIRED,False,"no active bond","MODEL_NOT_READY",{}); self.machine.transition(d.state,d.reason); self.last=d; return d
        reasons=list(extra_reasons); current=time.monotonic() if now is None else now
        if proximity_out_of_range:
            if self.proximity_out_of_range_since is None: self.proximity_out_of_range_since=current
        else: self.proximity_out_of_range_since=None
        if heartbeat_age is None or heartbeat_age>self.heartbeat_timeout: reasons.append("authenticated heartbeat expired")
        if ble_age is None or ble_age>self.ble_max_age: reasons.append("BLE observation stale")
        proximity_ready=not proximity_out_of_range or current-self.proximity_out_of_range_since>=self.proximity_lock_delay
        if proximity_out_of_range and not proximity_ready: reasons.append("proximity outside range during grace period")
        if proximity_out_of_range and proximity_ready: reasons.append("phone outside configured proximity")
        if os_locked: d=Decision(SecurityState.LOCKED,False,"OS is locked","READY" if models_ready else "MODEL_NOT_READY",{"reasons":reasons})
        elif reasons and proximity_ready: d=Decision(SecurityState.LOCK_PENDING,True,"; ".join(reasons),"READY" if models_ready else "MODEL_NOT_READY",{"reasons":reasons,"proximity_distance_meters":proximity_distance_meters})
        elif reasons: d=Decision(SecurityState.ARMED,False,"; ".join(reasons),"READY" if models_ready else "MODEL_NOT_READY",{"reasons":reasons,"proximity_distance_meters":proximity_distance_meters})
        else: d=Decision(SecurityState.ARMED,False,"phone present","READY" if models_ready else "MODEL_NOT_READY",{})
        self.machine.transition(d.state,d.reason); self.last=d; return d
    def apply(self,decision):
        if not decision.should_lock or self.lock_in_progress:return None
        self.lock_in_progress=True
        try:
            result=self.lock_callback(reason=decision.reason); self.machine.transition(SecurityState.LOCKED if result.confirmed else SecurityState.DEGRADED,decision.reason); return result
        finally:self.lock_in_progress=False