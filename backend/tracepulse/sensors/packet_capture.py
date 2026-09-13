# packet_capture.py
import asyncio,csv,ipaddress,shutil
from dataclasses import dataclass
@dataclass(frozen=True)
class PacketMetadata:
    timestamp_epoch:float; frame_length_bytes:int; source_ip:str|None; destination_ip:str|None; source_port:int|None; destination_port:int|None; tcp_flags:str|None
class DumpcapPacketCapture:
    def __init__(self,*,interface,peer_host,peer_port):
        ipaddress.ip_address(peer_host)
        if not interface or not 1<=peer_port<=65535: raise ValueError("invalid capture target")
        self.interface=interface; self.peer_host=peer_host; self.peer_port=peer_port; self.process=None
    async def start(self):
        if shutil.which("dumpcap") is None: raise FileNotFoundError("dumpcap")
        if self.process and self.process.returncode is None: raise RuntimeError("capture already running")
        bpf=f"host {self.peer_host} and port {self.peer_port}"
        self.process=await asyncio.create_subprocess_exec("dumpcap","-i",self.interface,"-l","-q","-T","fields","-E","header=n","-E","separator=,","-E","quote=n","-e","frame.time_epoch","-e","frame.len","-e","ip.src","-e","ip.dst","-e","tcp.srcport","-e","tcp.dstport","-e","tcp.flags","-f",bpf,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    async def packets(self):
        if not self.process or not self.process.stdout: raise RuntimeError("capture is not running")
        async for raw in self.process.stdout:
            try:
                f=next(csv.reader([raw.decode(errors="replace").strip()]))
                if len(f)<7: continue
                yield PacketMetadata(float(f[0]),int(f[1]),f[2] or None,f[3] or None,int(f[4]) if f[4] else None,int(f[5]) if f[5] else None,f[6] or None)
            except (ValueError,IndexError): continue
    async def stop(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try: await asyncio.wait_for(self.process.wait(),2)
            except asyncio.TimeoutError: self.process.kill(); await self.process.wait()
        self.process=None

# The BPF expression is fixed from validated constructor arguments. No network client supplies it and payloads are never stored.