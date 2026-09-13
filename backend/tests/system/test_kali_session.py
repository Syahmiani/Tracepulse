# Minimal test file for KaliSession
from tracepulse.os_integration.kali_session import KaliSession

def test_boolean_parser():
    assert KaliSession._bool("yes") is True
    assert KaliSession._bool("no") is False