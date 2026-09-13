# arp_guard.py
import re, shutil, subprocess
from dataclasses import dataclass
_NEIGHBOR=re.compile(r"^(\S+) dev (\S+)(?: lladdr ([0-9a-fA-F:]{17}))?(?: (\S+))?")
@dataclass(frozen=True)
class NeighborEntry: ip:str; interface:str; mac:str|None; state:str|None
class ArpGuard:
    def __init__(self): self.baseline=None
    def assess(self):
        if shutil.which("ip") is None: raise FileNotFoundError("ip")
        route=subprocess.run(["ip","-4","route","show","default"],capture_output=True,text=True,check=True).stdout.splitlines(); gateway=None; interface=None
        for line in route:
            p=line.split();
            if len(p)>=5 and p[0]=="default" and p[1]=="via": gateway,interface=p[2],p[4]; break
        entries=[]
        for line in subprocess.run(["ip","neigh","show"],capture_output=True,text=True,check=True).stdout.splitlines():
            m=_NEIGHBOR.match(line.strip())
            if m: entries.append(NeighborEntry(m.group(1),m.group(2),m.group(3).lower() if m.group(3) else None,m.group(4)))
        mac=next((x.mac for x in entries if x.ip==gateway and x.interface==interface),None); changed=bool(mac and self.baseline and mac!=self.baseline)
        if mac and self.baseline is None: self.baseline=mac
        by_ip={}
        for e in entries:
            if e.mac: by_ip.setdefault(e.ip,set()).add(e.mac)
        return {"gateway_ip":gateway,"gateway_mac":mac,"gateway_mac_changed":changed,"duplicate_ip_addresses":tuple(sorted(k for k,v in by_ip.items() if len(v)>1)),"neighbors":tuple(entries)}
