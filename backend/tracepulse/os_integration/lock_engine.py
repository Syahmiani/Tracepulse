from __future__ import annotations
import threading, time
from dataclasses import dataclass
from datetime import datetime, timezone
from .kali_session import KaliSession, KaliSessionError
@dataclass(frozen=True)
class UnlockAuthorization:
    verification_id:str; source:str; issued_at_epoch:float; expires_at_epoch:float; verified:bool; scope:str
    def valid(self,now=None):
        now=time.time() if now is None else now
        return self.verified and self.source in {"android_biometric","browser_demo"} and self.scope=="unlock_workstation" and bool(self.verification_id) and self.issued_at_epoch<=now<=self.expires_at_epoch
@dataclass(frozen=True)
class LockResult:
    action:str; requested:bool; confirmed:bool; dispatch_latency_ms:float; session_id:str|None; reason:str; command_succeeded:bool; message:str; captured_at_utc:str
class LockEngine:
    def __init__(self, session=None, state_confirmation_timeout_seconds=.8): self.session=session or KaliSession(); self.timeout=state_confirmation_timeout_seconds; self._lock=threading.Lock()
    def lock_now(self, *, reason): return self._operate("lock",reason)
    def unlock_authorized(self, *, authorization, reason="verified Android device authorization"):
        if not authorization.valid(): raise PermissionError("unlock authorization is invalid or expired")
        return self._operate("unlock",reason)
    def _operate(self, action, reason):
        if not reason.strip(): raise ValueError("reason is required")
        with self._lock:
            started=time.monotonic(); info=None; command_succeeded=False; message=""
            try:
                info=self.session.inspect()
                result=getattr(self.session,action)(info.session_id); command_succeeded=result.succeeded; message=getattr(result,"stderr","").strip() or getattr(result,"stdout","").strip()
                confirmed=False
                if command_succeeded:
                    state=self.session.wait_for_locked(action=="lock",session_id=info.session_id,timeout_seconds=self.timeout)
                    confirmed=state.locked_hint is (action=="lock")
                    if action=="lock" and not confirmed:
                        confirmed=getattr(self.session,"screen_locker_active",lambda:False)()
                return LockResult(action,True,confirmed,(time.monotonic()-started)*1000,info.session_id,reason,command_succeeded,message or f"{action} requested",datetime.now(timezone.utc).isoformat())
            except (KaliSessionError,OSError) as exc:
                return LockResult(action,True,False,(time.monotonic()-started)*1000,info.session_id if info else None,reason,command_succeeded,str(exc),datetime.now(timezone.utc).isoformat())