from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PerimeterReading:
    base_limit_meters: float
    effective_limit_meters: float
    expanded: bool
    reason: str


class DynamicPerimeter:
    """Deterministic (non-ML) perimeter sizing.

    This is a rule-based heuristic, not a trained model, so unlike
    ``ai/context_knn.py`` and ``ai/network_guard.py`` it can run safely
    today without any calibration data. The digital fence expands beyond
    the configured base limit only when both of the following hold:

    * the Kalman filter's covariance (``ai/kalman.py``) is low, meaning the
      BLE RSSI signal has settled rather than jumping around, and
    * the laptop is currently on a network context marked as trusted
      (``sensors/network_context.py``).

    Otherwise the perimeter holds (or returns to) the base limit. This
    keeps the fence conservative by default and only relaxes it when the
    system has good reason to believe the phone/laptop link is reliable.
    """

    def __init__(
        self,
        *,
        base_limit_meters: float,
        max_expansion_meters: float = 3.0,
        stability_covariance_threshold: float = 6.0,
    ):
        if base_limit_meters <= 0 or max_expansion_meters < 0 or stability_covariance_threshold <= 0:
            raise ValueError("invalid dynamic perimeter configuration")
        self.base_limit_meters = base_limit_meters
        self.max_expansion_meters = max_expansion_meters
        self.stability_covariance_threshold = stability_covariance_threshold

    def evaluate(self, *, rssi_covariance: float | None, network_is_trusted: bool | None) -> PerimeterReading:
        if rssi_covariance is None:
            return PerimeterReading(self.base_limit_meters, self.base_limit_meters, False, "no signal stability data yet")
        if not network_is_trusted:
            return PerimeterReading(self.base_limit_meters, self.base_limit_meters, False, "network context not confirmed trusted")
        if rssi_covariance <= self.stability_covariance_threshold:
            expanded = self.base_limit_meters + self.max_expansion_meters
            return PerimeterReading(self.base_limit_meters, expanded, True, "stable signal on trusted network")
        return PerimeterReading(self.base_limit_meters, self.base_limit_meters, False, "signal covariance too high to expand")
