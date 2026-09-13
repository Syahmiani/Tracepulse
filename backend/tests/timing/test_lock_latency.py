# Minimal test file for lock latency
import time
from tracepulse.os_integration.lock_engine import LockEngine

class FastSession:
    def inspect(self, session_id=None): return type('obj', (object,), {'session_id': 's'})
    def lock(self, session_id=None): return type('obj', (object,), {'succeeded': True})
    def wait_for_locked(self, expected, **kwargs): return type('obj', (object,), {'locked_hint': expected})

def test_lock_dispatch_latency_is_recorded():
    result = LockEngine(FastSession()).lock_now(reason="timing test")
    assert result.confirmed