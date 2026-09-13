from __future__ import annotations
import base64, hashlib, hmac, json, re, secrets, time
from dataclasses import dataclass
from typing import Any, Mapping
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_EVENT = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
class MessageIntegrityError(ValueError): pass

def canonical_json(value: Mapping[str, Any]) -> bytes:
    try: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError) as exc: raise MessageIntegrityError("non-canonical message") from exc

def derive_session_key(*, shared_secret: bytes, salt: bytes) -> bytes:
    if len(shared_secret) != 32 or len(salt) != 32: raise MessageIntegrityError("invalid key derivation inputs")
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"tracepulse/session-key/v1").derive(shared_secret)

def _b64(v: bytes) -> str: return base64.urlsafe_b64encode(v).decode().rstrip("=")
def _unb64(v: str) -> bytes: return base64.urlsafe_b64decode(v + "=" * (-len(v) % 4))

@dataclass(frozen=True)
class MessageEnvelope:
    version: int; session_id: str; sequence: int; timestamp_ms: int; nonce: str; event: str; payload: Mapping[str, Any]; hmac_b64: str
    def unsigned_dict(self): return {"version": self.version, "session_id": self.session_id, "sequence": self.sequence, "timestamp_ms": self.timestamp_ms, "nonce": self.nonce, "event": self.event, "payload": self.payload}
    def as_dict(self): return {**self.unsigned_dict(), "hmac": self.hmac_b64}
    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]):
        required = {"version","session_id","sequence","timestamp_ms","nonce","event","payload","hmac"}
        if not isinstance(value, Mapping) or not required.issubset(value): raise MessageIntegrityError("incomplete envelope")
        if not isinstance(value["payload"], Mapping): raise MessageIntegrityError("payload must be an object")
        return cls(int(value["version"]), str(value["session_id"]), int(value["sequence"]), int(value["timestamp_ms"]), str(value["nonce"]), str(value["event"]), dict(value["payload"]), str(value["hmac"]))

def sign_message(*, key: bytes, session_id: str, sequence: int, event: str, payload: Mapping[str, Any], timestamp_ms: int | None = None, nonce: str | None = None) -> MessageEnvelope:
    if len(key) != 32 or sequence < 0 or not session_id or not _EVENT.fullmatch(event): raise MessageIntegrityError("invalid message fields")
    env = MessageEnvelope(1, session_id, sequence, int(time.time()*1000) if timestamp_ms is None else int(timestamp_ms), nonce or _b64(secrets.token_bytes(16)), event, dict(payload), "")
    return MessageEnvelope(env.version, env.session_id, env.sequence, env.timestamp_ms, env.nonce, env.event, env.payload, _b64(hmac.new(key, canonical_json(env.unsigned_dict()), hashlib.sha256).digest()))

def verify_message(env: MessageEnvelope, *, key: bytes, expected_session_id: str, max_clock_skew_ms: int = 5000, now_ms: int | None = None) -> None:
    if len(key) != 32 or env.version != 1 or env.session_id != expected_session_id or env.sequence < 0 or not _EVENT.fullmatch(env.event): raise MessageIntegrityError("invalid authenticated message")
    try: supplied = _unb64(env.hmac_b64)
    except Exception as exc: raise MessageIntegrityError("invalid HMAC encoding") from exc
    expected = hmac.new(key, canonical_json(env.unsigned_dict()), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, supplied): raise MessageIntegrityError("message authentication failed")
    now = int(time.time()*1000) if now_ms is None else int(now_ms)
    if abs(now - env.timestamp_ms) > max_clock_skew_ms: raise MessageIntegrityError("message timestamp outside allowed window")