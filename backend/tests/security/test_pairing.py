# Minimal test file for pairing.py
from tracepulse.config import Config
from tracepulse.security.pairing import PairingManager


def test_pairing_challenge_is_created():
    manager = PairingManager()
    offer = manager.create_offer(service_url="https://127.0.0.1:8443/")
    assert offer.handle
    assert offer.token


def test_windows_local_mode_allows_http_service_url(monkeypatch):
    monkeypatch.setenv("TRACEPULSE_ALLOW_INSECURE_LOCAL", "true")
    monkeypatch.setenv("TRACEPULSE_SERVICE_URL", "http://127.0.0.1:8443/")
    config = Config.from_env()
    config.validate_runtime()
    assert config.service_url == "http://127.0.0.1:8443/"