from __future__ import annotations
import asyncio, math, random, time
from datetime import datetime, timezone
from .ble_rssi import BleObservation


class SimulatedBleRssiCollector:
    """Fakes a BLE RSSI stream for demo purposes only.

    Real BLE proximity needs the phone to *advertise* a BLE service, which
    a browser tab cannot do (the Web Bluetooth API only scans/connects, it
    never advertises). Until the phone side is a native app that can act as
    a BLE peripheral, there is no real RSSI to read. This collector produces
    a smooth, slowly-drifting synthetic signal instead, so the dashboard's
    Proximity Guard / Signal & Proximity panels have something to animate
    while presenting or developing the rest of the system.

    This must never be mistaken for real telemetry: every reading is
    reported through the same status API with ``"simulated": true`` set
    wherever proximity data is exposed (see ``Services.perimeter_snapshot``
    in app.py), and it is only ever used when the operator explicitly opts
    in via ``TRACEPULSE_BLE_SIMULATE=true``.
    """

    def __init__(self, *, service_uuid: str = "simulated", adapter: str | None = None, seed: int | None = None):
        self.service_uuid = service_uuid
        self.adapter = adapter
        self._rng = random.Random(seed)
        self._t0 = time.monotonic()

    def _synthetic_rssi(self) -> int:
        elapsed = time.monotonic() - self._t0
        # Slow sine sweep between roughly -50 dBm (close) and -85 dBm (far),
        # with a bit of jitter so the Kalman filter has something to smooth.
        center = -67.5
        swing = 17.5
        base = center + swing * math.sin(elapsed / 20.0)
        jitter = self._rng.uniform(-2.5, 2.5)
        rssi = int(round(base + jitter))
        return max(-95, min(-40, rssi))

    async def scan_once(self, timeout_seconds: float = 2.0) -> list[BleObservation]:
        now = time.monotonic()
        utc = datetime.now(timezone.utc).isoformat()
        return [BleObservation(utc, now, self._synthetic_rssi(), None, "Simulated Phone", self.service_uuid, "")]

    async def stream(self, scan_timeout_seconds: float = 2.0, interval_seconds: float = 0.5):
        while True:
            for item in await self.scan_once(scan_timeout_seconds):
                yield item
            await asyncio.sleep(interval_seconds)
