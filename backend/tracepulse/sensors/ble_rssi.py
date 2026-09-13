from __future__ import annotations
import asyncio, time
from dataclasses import dataclass
from datetime import datetime, timezone
from bleak import BleakScanner

@dataclass(frozen=True)
class BleObservation:
    observed_at_utc: str; timestamp_monotonic: float; rssi_dbm: int
    tx_power_dbm: int | None; local_name: str | None; service_uuid: str; service_data_hex: str

class BleRssiCollector:
    def __init__(self, *, service_uuid: str, adapter: str | None = None, expected_service_data_hex: str | None = None):
        if not service_uuid.strip(): raise ValueError("service_uuid is required")
        self.service_uuid=service_uuid.lower().replace("-",""); self.adapter=adapter
        self.expected=expected_service_data_hex.lower() if expected_service_data_hex else None
    async def scan_once(self, timeout_seconds=2.0) -> list[BleObservation]:
        if timeout_seconds<=0: raise ValueError("timeout must be positive")
        found=await BleakScanner.discover(timeout=timeout_seconds, adapter=self.adapter, return_adv=True)
        now=time.monotonic(); utc=datetime.now(timezone.utc).isoformat(); result=[]
        for _address,(device,adv) in found.items():
            for uuid,data in (getattr(adv,"service_data",{}) or {}).items():
                raw=bytes(data); normalized=str(uuid).lower().replace("-","")
                if normalized!=self.service_uuid or (self.expected and raw.hex()!=self.expected): continue
                rssi=int(adv.rssi)
                if not -127<=rssi<0: continue
                result.append(BleObservation(utc,now,rssi,int(adv.tx_power) if adv.tx_power is not None else None,getattr(device,"name",None),self.service_uuid,raw.hex()))
        return result
    async def stream(self, scan_timeout_seconds=2.0, interval_seconds=.1):
        while True:
            for item in await self.scan_once(scan_timeout_seconds): yield item
            if interval_seconds: await asyncio.sleep(interval_seconds)