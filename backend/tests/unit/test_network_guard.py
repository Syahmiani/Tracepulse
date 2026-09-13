# Minimal test file for network_guard.py
import pytest
from tracepulse.ai.network_guard import NetworkFeatures, NetworkGuard

def test_network_features_validate():
    sample = NetworkFeatures(400, 20, 80, 500, 20, 0.01, 0.01)
    assert sample.valid