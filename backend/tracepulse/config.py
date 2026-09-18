from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    service_url: str = "https://192.168.0.152:8443/"
    bind_host: str = "0.0.0.0"
    port: int = 8443
    database_path: str = "~/.local/share/tracepulse/tracepulse.sqlite3"
    tls_cert: str = "config/tls/server.crt"
    tls_key: str = "config/tls/server.key"
    ble_service_uuid: str = "7f5c6e7a-2f8a-4f3d-9a6b-1c0e8d4b2f91"
    ble_adapter: str = "hci0"
    heartbeat_timeout_seconds: float = 2.2
    ble_max_age_seconds: float = 3.0
    rssi_threshold_dbm: float = -75.0
    proximity_distance_meters: float = 8.0
    proximity_lock_delay_seconds: float = 5.0
    proximity_reference_rssi_dbm: float = -59.0
    proximity_path_loss_exponent: float = 2.0
    local_admin_only: bool = True
    local_status_only: bool = True
    calibration_mode: bool = False
    allow_insecure_local: bool = True
    testing: bool = False

    @classmethod
    def from_env(cls, testing: bool = False) -> "Config":
        return cls(
            service_url=os.getenv("TRACEPULSE_SERVICE_URL", cls.service_url),
            bind_host=os.getenv("TRACEPULSE_BIND_HOST", cls.bind_host),
            port=int(os.getenv("TRACEPULSE_PORT", cls.port)),
            database_path=os.getenv("TRACEPULSE_DATABASE_PATH", cls.database_path),
            tls_cert=os.getenv("TRACEPULSE_TLS_CERT", cls.tls_cert),
            tls_key=os.getenv("TRACEPULSE_TLS_KEY", cls.tls_key),
            ble_service_uuid=os.getenv("TRACEPULSE_BLE_SERVICE_UUID", cls.ble_service_uuid),
            ble_adapter=os.getenv("TRACEPULSE_BLE_ADAPTER", cls.ble_adapter),
            heartbeat_timeout_seconds=float(os.getenv("TRACEPULSE_HEARTBEAT_TIMEOUT_SECONDS", cls.heartbeat_timeout_seconds)),
            ble_max_age_seconds=float(os.getenv("TRACEPULSE_BLE_MAX_AGE_SECONDS", cls.ble_max_age_seconds)),
            rssi_threshold_dbm=float(os.getenv("TRACEPULSE_RSSI_THRESHOLD_DBM", cls.rssi_threshold_dbm)),
            proximity_distance_meters=float(os.getenv("TRACEPULSE_PROXIMITY_DISTANCE_METERS", cls.proximity_distance_meters)),
            proximity_lock_delay_seconds=float(os.getenv("TRACEPULSE_PROXIMITY_LOCK_DELAY_SECONDS", cls.proximity_lock_delay_seconds)),
            proximity_reference_rssi_dbm=float(os.getenv("TRACEPULSE_PROXIMITY_REFERENCE_RSSI_DBM", cls.proximity_reference_rssi_dbm)),
            proximity_path_loss_exponent=float(os.getenv("TRACEPULSE_PROXIMITY_PATH_LOSS_EXPONENT", cls.proximity_path_loss_exponent)),
            local_admin_only=_env_bool("TRACEPULSE_LOCAL_ADMIN_ONLY", cls.local_admin_only),
            local_status_only=_env_bool("TRACEPULSE_LOCAL_STATUS_ONLY", cls.local_status_only),
            calibration_mode=_env_bool("TRACEPULSE_CALIBRATION_MODE", cls.calibration_mode),
            allow_insecure_local=_env_bool("TRACEPULSE_ALLOW_INSECURE_LOCAL", cls.allow_insecure_local),
            testing=testing,
        )

    def validate_runtime(self) -> None:
        if self.service_url.startswith("http://"):
            if not self.allow_insecure_local:
                raise ValueError("HTTP service URLs require TRACEPULSE_ALLOW_INSECURE_LOCAL=true")
        elif self.service_url.startswith("https://"):
            pass
        else:
            raise ValueError("service_url must use HTTP or HTTPS")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.heartbeat_timeout_seconds <= 0 or self.ble_max_age_seconds <= 0:
            raise ValueError("sensor timeouts must be positive")
        if self.proximity_distance_meters <= 0 or self.proximity_lock_delay_seconds <= 0:
            raise ValueError("proximity distance and lock delay must be positive")
        if not -127 < self.proximity_reference_rssi_dbm < 0 or self.proximity_path_loss_exponent <= 0:
            raise ValueError("invalid proximity calibration")
