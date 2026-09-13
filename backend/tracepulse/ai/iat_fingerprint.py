from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class IATSequence:
    intervals_ms:tuple[float,...]; device_label:str
    def __post_init__(self):
        if len(self.intervals_ms)<10 or any(x<=0 for x in self.intervals_ms): raise ValueError("at least ten positive IAT values are required")
def extract_iat_features(sequence):
    values=sorted(float(x) for x in sequence.intervals_ms); n=len(values); q=lambda p:values[min(n-1,int(p*(n-1)))]
    mean=sum(values)/n; variance=sum((x-mean)**2 for x in values)/n
    return {"mean_ms":mean,"std_ms":variance**.5,"median_ms":q(.5),"p05_ms":q(.05),"p95_ms":q(.95)}
class IATFingerprintModel:
    fitted=False
    def predict(self,*args,**kwargs): raise RuntimeError("MODEL_NOT_READY")
class IATProfileDetector(IATFingerprintModel): pass