# wifi_scanner.py
import re, shutil, subprocess
from dataclasses import dataclass
_MAC=re.compile(r"^(?P<mac>(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}):(?P<rest>.*)$")
@dataclass(frozen=True)
class WiFiNetwork: bssid:str; ssid:str; channel:str|None; rate:str|None; signal_percent:int|None; security:str|None; in_use:bool
class WiFiScanner:
    def scan(self, *, interface=None, rescan=False):
        if shutil.which("nmcli") is None: raise FileNotFoundError("nmcli")
        cmd=["nmcli","-t","-e","no","-f","IN-USE,BSSID,SSID,CHAN,RATE,SIGNAL,SECURITY","dev","wifi","list"]
        if interface: cmd += ["ifname",interface]
        cmd += ["--rescan","yes" if rescan else "no"]; result=[]
        for line in subprocess.run(cmd,capture_output=True,text=True,timeout=15,check=True).stdout.splitlines():
            used,sep,rest=line.partition(":"); m=_MAC.match(rest)
            if not sep or not m: continue
            f=m.group("rest").rsplit(":",4)
            if len(f)!=5: continue
            try: signal=int(f[3]) if f[3] else None
            except ValueError: signal=None
            result.append(WiFiNetwork(m.group("mac").lower(),f[0],f[1] or None,f[2] or None,signal,f[4] or None,used=="*"))
        return result