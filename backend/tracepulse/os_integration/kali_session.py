from __future__ import annotations
import os, pwd, shutil, subprocess, time
from dataclasses import dataclass

class KaliSessionError(RuntimeError): pass
@dataclass(frozen=True)
class SessionCommandResult:
    command: tuple[str,...]; return_code:int; stdout:str; stderr:str
    @property
    def succeeded(self): return self.return_code==0
@dataclass(frozen=True)
class KaliSessionInfo:
    session_id:str; user:str; session_type:str; session_class:str; state:str; active:bool; remote:bool; locked_hint:bool|None
    @property
    def graphical(self): return self.session_type in {"x11","wayland"}
class KaliSession:
    def __init__(self, command_timeout_seconds=3): self.timeout=command_timeout_seconds
    def _run(self,args):
        if shutil.which("loginctl") is None: raise KaliSessionError("loginctl was not found")
        p=subprocess.run(args,capture_output=True,text=True,timeout=self.timeout,check=False)
        return SessionCommandResult(tuple(args),p.returncode,p.stdout,p.stderr)
    def _properties(self, session_id):
        result=self._run(["loginctl","show-session",session_id,"-p","Id","-p","User","-p","Type","-p","Class","-p","State","-p","Active","-p","Remote","-p","LockedHint"])
        if not result.succeeded: raise KaliSessionError(result.stderr.strip() or "cannot inspect session")
        return dict(line.split("=",1) for line in result.stdout.splitlines() if "=" in line)
    @staticmethod
    def _bool(value): return str(value).lower() in {"1","yes","true"}
    def inspect(self, session_id=None):
        current_user=pwd.getpwuid(os.getuid()).pw_name
        sid=session_id or os.environ.get("XDG_SESSION_ID")
        if sid is None:
            listed=self._run(["loginctl","list-sessions","--no-legend"])
            if not listed.succeeded: raise KaliSessionError(listed.stderr.strip() or "cannot list sessions")
            candidates=[]
            for line in listed.stdout.splitlines():
                fields=line.split()
                if len(fields)>=2 and fields[1]==current_user:
                    try: candidates.append(self._build(self._properties(fields[0])))
                    except KaliSessionError: pass
            candidates=[x for x in candidates if x.active and not x.remote and x.graphical]
            if not candidates: raise KaliSessionError("no active local graphical session")
            return candidates[0]
        info=self._build(self._properties(sid))
        if info.user!=current_user or info.remote or not info.graphical: raise KaliSessionError("session is not the current local graphical session")
        return info
    def _build(self,p):
        if not p.get("Id") or not p.get("User"): raise KaliSessionError("session did not expose Id/User")
        return KaliSessionInfo(p["Id"],p["User"],p.get("Type", ""),p.get("Class", ""),p.get("State", ""),self._bool(p.get("Active")),self._bool(p.get("Remote")),self._bool(p["LockedHint"]) if "LockedHint" in p else None)
    def lock(self, session_id=None):
        info=self.inspect(session_id); return self._run(["loginctl","lock-session",info.session_id])
    def unlock(self, session_id=None):
        info=self.inspect(session_id); return self._run(["loginctl","unlock-session",info.session_id])
    def wait_for_locked(self, expected, *, session_id=None, timeout_seconds=.8, poll_seconds=.05):
        deadline=time.monotonic()+timeout_seconds; last=None
        while time.monotonic()<=deadline:
            last=self.inspect(session_id)
            if last.locked_hint is expected: return last
            time.sleep(poll_seconds)
        raise KaliSessionError(f"OS did not confirm LockedHint={expected}; last={last}")