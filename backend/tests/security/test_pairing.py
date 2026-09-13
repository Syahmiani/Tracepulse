# Minimal test file for pairing.py
from tracepulse.security.pairing import PairingManager

def test_pairing_challenge_is_created():
    manager = PairingManager()
    offer = manager.create_offer(service_url="https://127.0.0.1:8443/")
    assert offer.handle
    assert offer.token