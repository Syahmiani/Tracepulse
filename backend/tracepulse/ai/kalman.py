from __future__ import annotations
import math,time
from dataclasses import dataclass
@dataclass(frozen=True)
class KalmanEstimate:
    measurement_dbm:float; filtered_dbm:float; covariance:float; accepted:bool; timestamp_monotonic:float
class KalmanFilter1D:
    def __init__(self,measurement_variance=9.0,process_variance_per_second=1.0,outlier_gate_sigma=5.0): self.r=measurement_variance; self.q=process_variance_per_second; self.gate=outlier_gate_sigma; self.reset()
    def reset(self): self.initialized=False; self.x=0.0; self.p=25.0; self.last_time=None
    def update(self,measurement_dbm,timestamp_monotonic=None):
        if not math.isfinite(measurement_dbm) or not -127<=measurement_dbm<0: raise ValueError("RSSI must be a negative dBm value")
        now=time.monotonic() if timestamp_monotonic is None else float(timestamp_monotonic)
        if self.last_time is not None and now<self.last_time: raise ValueError("timestamp moved backwards")
        if not self.initialized: self.initialized=True; self.x=measurement_dbm; self.last_time=now; return KalmanEstimate(measurement_dbm,self.x,self.p,True,now)
        dt=max(1e-6,now-self.last_time); predicted=self.p+self.q*dt; innovation=measurement_dbm-self.x; std=math.sqrt(predicted+self.r); accepted=abs(innovation)/std<=self.gate
        if accepted: gain=predicted/(predicted+self.r); self.x+=gain*innovation; self.p=(1-gain)*predicted
        else: self.p=predicted
        self.last_time=now; return KalmanEstimate(measurement_dbm,self.x,self.p,accepted,now)