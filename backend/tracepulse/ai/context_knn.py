from __future__ import annotations
import math
from dataclasses import dataclass
@dataclass(frozen=True)
class ContextSample:
    nearby_bssid_count:float; wifi_signal_dbm:float; wifi_is_trusted:float; wifi_is_encrypted:float; ble_rssi_mean_dbm:float; ble_rssi_std_db:float; ble_rssi_trend_db_per_second:float; heartbeat_jitter_ms:float; packet_loss_rate:float; hour_of_day:float
    def vector(self):
        values=[float(getattr(self,name)) for name in self.__dataclass_fields__]
        if not all(math.isfinite(x) for x in values) or not -120<=self.wifi_signal_dbm<=0 or not -120<=self.ble_rssi_mean_dbm<=0: raise ValueError("invalid context sample")
        return values
@dataclass(frozen=True)
class ContextPrediction: label:str; probabilities:dict[str,float]; risk_score:float; model_version:str
class ContextRiskClassifier:
    def __init__(self): self.pipeline=None; self.model_version="untrained"
    @property
    def fitted(self): return self.pipeline is not None
    def fit(self,*args,**kwargs): raise RuntimeError("MODEL_NOT_READY: train offline from real labelled sessions")
    def predict(self,sample):
        sample.vector()
        if not self.fitted: raise RuntimeError("MODEL_NOT_READY")
        return self.pipeline.predict(sample.vector())