from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
import threading
class SecurityState(str,Enum): UNPAIRED="unpaired"; ARMED="armed"; DEGRADED="degraded"; LOCK_PENDING="lock_pending"; LOCKED="locked"
@dataclass(frozen=True)
class StateChange: previous:SecurityState; current:SecurityState; reason:str
class SecurityStateMachine:
    def __init__(self): self._state=SecurityState.UNPAIRED; self._lock=threading.RLock()
    @property
    def state(self):
        with self._lock:return self._state
    def transition(self,target,reason):
        if not reason.strip(): raise ValueError("transition reason is required")
        with self._lock:
            previous=self._state; self._state=SecurityState(target); return StateChange(previous,self._state,reason)