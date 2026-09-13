from __future__ import annotations
import ipaddress, re, shutil, subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
import psutil

_MAC=re.compile(r"^(?P<mac>(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}):(?P<rest>.*)$")
_ROUTE=re.compile(r"^default via (?P<gateway>\S+) dev (?P<interface>\S+)")
@dataclass(frozen=True)
class NetworkContext:
    captured_at_utc: str; interface: str|None; ssid: str|None; bssid: str|None; signal_percent: int|None; security: str|None; nearby_bssid_count: int; gateway_ip: str|None; rx_bytes: int; tx_bytes: int; wifi_is_trusted: bool; wifi_is_encrypted: bool
class NetworkContextCollector:
    def __init__(self, *, interface=None, trusted_bssids=(), command_timeout_seconds=5):
        self.interface=interface; self.trusted={self._mac(x) for x in trusted_bssids}; self.timeout=command_timeout_seconds
    @staticmethod
    def _mac(value): return value.strip().lower().replace("-",":")
    def _run(self,args):
        if shutil.which(args[0]) is None: raise FileNotFoundError(args[0])
        return subprocess.run(args,capture_output=True,text=True,timeout=self.timeout,check=True).stdout
    def _wifi(self):
        out=self._run(["nmcli","-t","-e","no","-f","ACTIVE,BSSID,SSID,SIGNAL,SECURITY","dev","wifi","list"])
        for line in out.splitlines():
            active,sep,rest=line.partition(":")
            match=_MAC.match(rest)
            if active!="yes" or not match: continue
            fields=match.group("rest").rsplit(":",2)
            if len(fields)!=3: continue
            ssid,signal,security=fields
            try: signal_value=int(signal)
            except ValueError: signal_value=None
            return match.group("mac").lower(), ssid or None, signal_value, security or None
        return None,None,None,None
    def _route(self):
        for line in self._run(["ip","-4","route","show","default"]).splitlines():
            m=_ROUTE.match(line.strip())
            if m: ipaddress.ip_address(m.group("gateway")); return m.group("gateway"),m.group("interface")
        return None,None
    def collect(self, nearby_bssid_count=0):
        bssid,ssid,signal,security=self._wifi(); gateway,route_interface=self._route(); interface=self.interface or route_interface
        counters=psutil.net_io_counters(pernic=True).get(interface) if interface else None; normalized=self._mac(bssid) if bssid else None; sec=(security or "").upper()
        return NetworkContext(datetime.now(timezone.utc).isoformat(),interface,ssid,normalized,signal,security,nearby_bssid_count,gateway,int(counters.bytes_recv) if counters else 0,int(counters.bytes_sent) if counters else 0,normalized in self.trusted if normalized else False,bool(sec and sec not in {"--","NONE","OPEN"}))