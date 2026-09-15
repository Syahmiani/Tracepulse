from tracepulse.ai.kalman import rssi_to_distance_meters
from tracepulse.decision_engine import DecisionEngine
from tracepulse.state_machine import SecurityState, SecurityStateMachine


def test_eight_meter_calibration_is_distance_based():
    assert round(rssi_to_distance_meters(-77.0618), 1) == 8.0


def test_proximity_requires_five_continuous_seconds_before_lock():
    engine = DecisionEngine(
        state_machine=SecurityStateMachine(),
        lock_callback=lambda reason: None,
        proximity_lock_delay_seconds=5.0,
    )
    first = engine.evaluate(session_active=True, heartbeat_age=0.1, ble_age=0.1, filtered_rssi_dbm=-80, proximity_out_of_range=True, proximity_distance_meters=9.0, os_locked=False, now=10.0)
    before_delay = engine.evaluate(session_active=True, heartbeat_age=0.1, ble_age=0.1, filtered_rssi_dbm=-80, proximity_out_of_range=True, proximity_distance_meters=9.0, os_locked=False, now=14.9)
    after_delay = engine.evaluate(session_active=True, heartbeat_age=0.1, ble_age=0.1, filtered_rssi_dbm=-80, proximity_out_of_range=True, proximity_distance_meters=9.0, os_locked=False, now=15.0)
    back_in_range = engine.evaluate(session_active=True, heartbeat_age=0.1, ble_age=0.1, filtered_rssi_dbm=-60, proximity_out_of_range=False, proximity_distance_meters=1.0, os_locked=False, now=15.1)
    assert first.state is SecurityState.ARMED and not first.should_lock
    assert before_delay.state is SecurityState.ARMED and not before_delay.should_lock
    assert after_delay.should_lock
    assert back_in_range.state is SecurityState.ARMED and not back_in_range.should_lock