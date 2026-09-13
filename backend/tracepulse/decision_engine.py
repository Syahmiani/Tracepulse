from __future__ import annotations
from dataclasses import dataclass
from .state_machine import SecurityState,SecurityStateMachine
@dataclass(frozen=True)
class Decision: state:SecurityState; should_lock:bool; reason:str; model_state:str; evidence:dict
class DecisionEngine:
    def __init__(self,*,state_machine:SecurityStateMachine,lock_callback,heartbeat_timeout_seconds=2.2,ble_max_age_seconds=3.0,rssi_threshold_dbm=None): self.machine=state_machine; self.lock_callback=lock_callback; self.heartbeat_timeout=heartbeat_timeout_seconds; self.ble_max_age=ble_max_age_seconds; self.rssi_threshold=rssi_threshold_dbm; self.last=None; self.lock_in_progress=False
    def evaluate(self,*,session_active,heartbeat_age,ble_age,filtered_rssi_dbm,os_locked,extra_reasons=(),models_ready=False):
        if not session_active: d=Decision(SecurityState.UNPAIRED,False,"no active bond","MODEL_NOT_READY",{}); self.machine.transition(d.state,d.reason); self.last=d; return d
        reasons=list(extra_reasons)
        if heartbeat_age is None or heartbeat_age>self.heartbeat_timeout: reasons.append("authenticated heartbeat expired")
        if ble_age is None or ble_age>self.ble_max_age: reasons.append("BLE observation stale")
        if self.rssi_threshold is not None and filtered_rssi_dbm is not None and filtered_rssi_dbm<self.rssi_threshold: reasons.append("filtered RSSI below calibrated threshold")
        if os_locked: d=Decision(SecurityState.LOCKED,False,"OS is locked","READY" if models_ready else "MODEL_NOT_READY",{"reasons":reasons})
        elif reasons: d=Decision(SecurityState.LOCK_PENDING,True,"; ".join(reasons),"READY" if models_ready else "MODEL_NOT_READY",{"reasons":reasons})
        else: d=Decision(SecurityState.ARMED,False,"phone present","READY" if models_ready else "MODEL_NOT_READY",{})
        self.machine.transition(d.state,d.reason); self.last=d; return d
    def apply(self,decision):
        if not decision.should_lock or self.lock_in_progress:return None
        self.lock_in_progress=True
        try:
            result=self.lock_callback(reason=decision.reason); self.machine.transition(SecurityState.LOCKED if result.confirmed else SecurityState.DEGRADED,decision.reason); return result
        finally:self.lock_in_progress=False