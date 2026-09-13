from dataclasses import dataclass
class ModelNotReady(RuntimeError): pass
@dataclass(frozen=True)
class ModelMetadata:
    name:str; version:str; feature_schema:tuple[str,...]; dataset_sha256:str; sample_count:int; status:str; metrics:dict
class ModelRegistry:
    def __init__(self): self._items={}
    def register(self,metadata,model):
        if metadata.status!="ready" or metadata.sample_count<=0 or len(metadata.dataset_sha256)!=64: raise ValueError("invalid model metadata")
        self._items[metadata.name]=(metadata,model)
    def get(self,name):
        if name not in self._items: raise ModelNotReady(f"{name}: MODEL_NOT_READY")
        return self._items[name]
    def metadata(self): return [item[0] for item in self._items.values()]