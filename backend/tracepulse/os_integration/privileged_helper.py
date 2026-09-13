from __future__ import annotations
import json,os,re,stat,subprocess
from pathlib import Path
_SESSION=re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
class PrivilegedHelperError(RuntimeError): pass
class PrivilegedHelperClient:
    def __init__(self,executable,timeout_seconds=2):
        self.path=Path(executable).resolve(); self.timeout=timeout_seconds
        if not self.path.is_file() or not os.access(self.path,os.X_OK): raise PrivilegedHelperError("helper is not executable")
        mode=stat.S_IMODE(self.path.stat().st_mode)
        if mode&0o022 or self.path.stat().st_uid!=0: raise PrivilegedHelperError("helper must be root-owned and non-writable")
    def execute(self,*,operation,session_id):
        if operation not in {"lock","unlock"} or not _SESSION.fullmatch(session_id): raise PrivilegedHelperError("invalid helper request")
        result=subprocess.run([str(self.path),"--operation",operation,"--session-id",session_id,"--json"],capture_output=True,text=True,timeout=self.timeout,check=False)
        try: payload=json.loads(result.stdout)
        except json.JSONDecodeError as exc: raise PrivilegedHelperError("helper returned invalid JSON") from exc
        if payload.get("session_id")!=session_id or not isinstance(payload.get("locked"),bool): raise PrivilegedHelperError("helper response failed validation")
        return {"succeeded":result.returncode==0 and payload.get("success") is True,"locked":payload["locked"],"message":str(payload.get("message",""))}