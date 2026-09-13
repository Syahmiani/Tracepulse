from dataclasses import dataclass
@dataclass(frozen=True)
class Explanation:
    category:str; severity:str; title:str; summary:str; evidence:tuple[str,...]; recommended_action:str
    def as_dict(self): return {"category":self.category,"severity":self.severity,"title":self.title,"summary":self.summary,"evidence":list(self.evidence),"recommended_action":self.recommended_action}
def explain_lock(reason,confirmed): return Explanation("lock","critical","Workstation lock requested",reason,(f"OS confirmation={confirmed}",),"Verify the Kali lock screen before continuing.")
def explain_model_not_ready(name): return Explanation("model","medium","Model not ready",f"{name} has no reviewed real-data artifact",("MODEL_NOT_READY",),"Collect and validate real calibration data.")