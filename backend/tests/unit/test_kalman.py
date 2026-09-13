# Minimal test file for kalman.py
from tracepulse.ai.kalman import KalmanFilter1D

def test_kalman_accepts_negative_rssi():
    f = KalmanFilter1D()
    first = f.update(-50.0, 1.0)
    second = f.update(-52.0, 1.2)
    assert first.accepted and second.accepted
    assert second.filtered_dbm < 0