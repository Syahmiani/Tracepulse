from __future__ import annotations
import math, time
from dataclasses import dataclass
@dataclass(frozen=True)
class HeartbeatObservation:
    sequence: int; received_monotonic: float; payload_size_bytes: int; inter_arrival_ms: float | None; round_trip_ms: float | None
class HeartbeatMonitor:
    def __init__(self, timeout_seconds=2.2):
        if timeout_seconds<=0: raise ValueError("timeout must be positive")
        self.timeout_seconds=timeout_seconds; self._last=None; self._last_sequence=None; self.received_count=0
    @property
    def last_observation(self): return self._last
    def record(self, *, sequence, payload_size_bytes, round_trip_ms=None, received_monotonic=None):
        now=time.monotonic() if received_monotonic is None else float(received_monotonic)
        if sequence<0 or payload_size_bytes<0 or not math.isfinite(now): raise ValueError("invalid heartbeat")
        if round_trip_ms is not None and (not math.isfinite(round_trip_ms) or round_trip_ms<0): raise ValueError("invalid RTT")
        if self._last and (sequence<=self._last_sequence or now<self._last.received_monotonic): raise ValueError("heartbeat order violation")
        iat=None if self._last is None else (now-self._last.received_monotonic)*1000
        self._last=HeartbeatObservation(sequence,now,payload_size_bytes,iat,round_trip_ms); self._last_sequence=sequence; self.received_count+=1; return self._last
    def age_seconds(self, now=None):
        if self._last is None: return None
        age=(time.monotonic() if now is None else now)-self._last.received_monotonic
        if age<0: raise ValueError("clock moved backwards")
        return age
    def expired(self, now=None):
        age=self.age_seconds(now); return age is None or age>self.timeout_seconds
    def reset(self): self._last=None; self._last_sequence=None; self.received_count=0