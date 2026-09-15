# sessions.py
from __future__ import annotations
import base64, secrets, threading, time
from dataclasses import dataclass, field, replace
from enum import Enum
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .message_integrity import canonical_json, derive_session_key

class SessionStatus(str, Enum):
    ACTIVE="active"; REVOKED="revoked"; EXPIRED="expired"

@dataclass(frozen=True)
class SessionRecord:
    session_id: str; device_label: str; created_at_epoch: float; last_seen_epoch: float; status: SessionStatus
    key: bytes = field(repr=False); key_salt: bytes = field(repr=False); device_signing_public_key: bytes = field(repr=False)
    outbound_sequence: int = 0
    approved: bool = False

class SessionError(ValueError): pass

@dataclass(frozen=True)
class UnlockAssertion:
    nonce: str; verification_id: str; issued_at_epoch: float; expires_at_epoch: float; signature_b64: str
    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict): raise SessionError("unlock assertion must be an object")
        try:
            return cls(str(value["nonce"]), str(value["verification_id"]), float(value["issued_at_epoch"]), float(value["expires_at_epoch"]), str(value["signature_b64"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise SessionError("malformed unlock assertion") from exc

def verify_unlock_assertion(assertion: UnlockAssertion, *, session_id: str, expected_nonce: str, public_key: bytes, now: float | None = None) -> bool:
    current=time.time() if now is None else float(now)
    if len(public_key)!=32 or assertion.nonce!=expected_nonce or not (assertion.issued_at_epoch<=current<=assertion.expires_at_epoch) or assertion.expires_at_epoch<assertion.issued_at_epoch or assertion.expires_at_epoch-assertion.issued_at_epoch>30:
        return False
    signed=canonical_json({"expires_at_epoch":int(assertion.expires_at_epoch) if assertion.expires_at_epoch.is_integer() else assertion.expires_at_epoch,"issued_at_epoch":int(assertion.issued_at_epoch) if assertion.issued_at_epoch.is_integer() else assertion.issued_at_epoch,"nonce":assertion.nonce,"session_id":session_id,"verification_id":assertion.verification_id,"version":1})
    try:
        padded=assertion.signature_b64+"="*((4-len(assertion.signature_b64)%4)%4)
        Ed25519PublicKey.from_public_bytes(public_key).verify(base64.urlsafe_b64decode(padded),signed)
        return True
    except Exception:
        return False

class SessionManager:
    def __init__(self, idle_timeout_seconds=30.0): self.idle_timeout_seconds=idle_timeout_seconds; self._active=None; self._lock=threading.RLock()
    def establish(self, *, shared_secret: bytes, device_label: str, device_signing_public_key: bytes) -> SessionRecord:
        if len(shared_secret)!=32 or len(device_signing_public_key)!=32 or not device_label.strip(): raise SessionError("invalid session inputs")
        with self._lock:
            if self._active and self._active.status is SessionStatus.ACTIVE: raise SessionError("an active session already exists")
            salt=secrets.token_bytes(32); now=time.time(); record=SessionRecord(secrets.token_urlsafe(32),device_label,now,now,SessionStatus.ACTIVE,derive_session_key(shared_secret=shared_secret,salt=salt),salt,bytes(device_signing_public_key)); self._active=record; return record
    def active(self):
        with self._lock:
            self._expire(); return self._active
    def require_active(self, session_id):
        record=self.active()
        if record is None or record.status is not SessionStatus.ACTIVE or not secrets.compare_digest(record.session_id,session_id): raise SessionError("no matching active session")
        return record
    def touch(self, session_id):
        with self._lock: self._active=replace(self.require_active(session_id),last_seen_epoch=time.time())
    def next_outbound_sequence(self, session_id):
        with self._lock:
            current=self.require_active(session_id); result=current.outbound_sequence; self._active=replace(current,outbound_sequence=result+1); return result
    def revoke(self, reason="unspecified"):
        with self._lock:
            if self._active: self._active=replace(self._active,status=SessionStatus.REVOKED)

    def reset(self) -> None:
        with self._lock:
            self._active = None
    def approve(self, session_id):
        with self._lock:
            self._active = replace(self.require_active(session_id), approved=True)
    def _expire(self):
        if (self._active and self._active.status is SessionStatus.ACTIVE
                and not self._active.approved
                and time.time()-self._active.last_seen_epoch>self.idle_timeout_seconds):
            self._active=replace(self._active,status=SessionStatus.EXPIRED)