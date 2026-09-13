from __future__ import annotations
import base64
from typing import Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def derive_session_key(shared_secret: bytes, salt: bytes) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"tracepulse/session-key/v1",
        backend=None
    )
    return hkdf.derive(shared_secret)


def sign_envelope(key: bytes, session_id: str, sequence: int, event: str, payload: Any) -> dict:
    unsigned = {
        "version": 1,
        "session_id": session_id,
        "sequence": sequence,
        "timestamp_ms": int(time.time() * 1000),
        "nonce": base64.urlsafe_b64encode(os.urandom(16)).decode("ascii").rstrip("="),
        "event": event,
        "payload": payload
    }
    canonical = canonical_json(unsigned)
    hmac = hmac.new(key, canonical.encode(), hashes.SHA256()).digest()
    return {
        **unsigned,
        "hmac": base64.urlsafe_b64encode(hmac).decode("ascii").rstrip("=")
    }


def verify_envelope(envelope: dict, key: bytes, expected_session_id: str) -> bool:
    if envelope.get("version") != 1 or envelope.get("session_id") != expected_session_id:
        return False
    unsigned = {k: v for k, v in envelope.items() if k != "hmac"}
    canonical = canonical_json(unsigned)
    expected_hmac = base64.urlsafe_b64decode(envelope["hmac"])
    computed_hmac = hmac.new(key, canonical.encode(), hashes.SHA256()).digest()
    return hmac.compare_digest(expected_hmac, computed_hmac)


def canonical_json(value: Any) -> str:
    if isinstance(value, dict):
        sorted_dict = {k: canonical_json(v) for k, v in sorted(value.items())}
        return json.dumps(sorted_dict, sort_keys=True)
    elif isinstance(value, list):
        return json.dumps([canonical_json(v) for v in value], sort_keys=True)
    else:
        return json.dumps(value)