# replay_guard.py
import threading
class ReplayError(ValueError): pass
class ReplayGuard:
    def __init__(self): self._highest=-1; self._nonces=set(); self._lock=threading.Lock()
    def check_and_record(self, envelope):
        with self._lock:
            if envelope.sequence <= self._highest: raise ReplayError("sequence is not strictly increasing")
            if not envelope.nonce or envelope.nonce in self._nonces: raise ReplayError("nonce was replayed")
            self._highest=envelope.sequence; self._nonces.add(envelope.nonce)
            if len(self._nonces)>10000: self._nonces.pop()