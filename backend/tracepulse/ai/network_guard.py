from __future__ import annotations
import math
from dataclasses import dataclass
@dataclass(frozen=True)
class NetworkFeatures:
    heartbeat_iat_mean_ms:float; heartbeat_iat_std_ms:float; heartbeat_rtt_p95_ms:float; packet_size_mean_bytes:float; packet_size_std_bytes:float; packet_loss_rate:float; sequence_gap_rate:float; reconnect_rate:float=0.0; tcp_reset_count:float=0.0; retransmission_rate:float=0.0
    @property
    def valid(self):
        try: self.vector(); return True
        except ValueError: return False
    def vector(self):
        values=[float(getattr(self,name)) for name in self.__dataclass_fields__]
        if not all(math.isfinite(x) and x>=0 for x in values): raise ValueError("invalid network features")
        if any(values[i]>1 for i in (5,6,7,9)): raise ValueError("rate must be between zero and one")
        return values
@dataclass(frozen=True)
class NetworkDecision:
    is_anomaly:bool; decision_score:float; model_version:str
class NetworkGuard:
    def __init__(self): self.pipeline=None; self.model_version="untrained"
    @property
    def fitted(self): return self.pipeline is not None
    def fit(self,*args,**kwargs): raise RuntimeError("MODEL_NOT_READY: train offline from real network data")
    def predict(self,features):
        features.vector()
        if not self.fitted: raise RuntimeError("MODEL_NOT_READY")
        return self.pipeline.predict(features.vector())