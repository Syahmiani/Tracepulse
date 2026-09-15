from __future__ import annotations

import base64, hashlib, hmac, secrets, threading, time
from dataclasses import dataclass, field
from urllib.parse import urlencode, urlsplit, urlunsplit
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def unb64(value: str) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError("invalid base64 value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def confirmation_key(shared: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b"tracepulse/pairing-confirmation/v1").derive(shared)


@dataclass(frozen=True)
class PairingOffer:
    handle: str; token: str; qr_payload: str; expires_at_epoch: float; server_public_key_b64: str

@dataclass(frozen=True)
class PairingChallenge:
    handle: str; challenge_b64: str; server_public_key_b64: str; expires_at_epoch: float

@dataclass(frozen=True)
class PairingResult:
    handle: str
    shared_secret: bytes = field(repr=False)
    challenge_b64: str
    server_confirmation_b64: str
    phone_public_key_b64: str
    device_signing_public_key_b64: str
    server_public_key_b64: str

@dataclass
class _Transaction:
    handle: str; token_hash: bytes; expires_at_epoch: float; server_private_key: X25519PrivateKey
    challenge: bytes | None = None

class PairingError(ValueError): pass

class PairingManager:
    def __init__(self, max_active_transactions: int = 8):
        self.max_active_transactions = max_active_transactions
        self._items: dict[str, _Transaction] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _check_url(url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query:
            raise PairingError("service_url must be an HTTPS URL without a query")

    def create_offer(self, *, service_url: str, ttl_seconds: float = 120) -> PairingOffer:
        self._check_url(service_url)
        if not 1 <= ttl_seconds <= 600: raise PairingError("invalid offer lifetime")
        with self._lock:
            self._purge()
            if len(self._items) >= self.max_active_transactions: raise PairingError("too many pairing offers")
            handle, token = secrets.token_urlsafe(18), secrets.token_urlsafe(32)
            private = X25519PrivateKey.generate(); expires = time.time() + ttl_seconds
            public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            parsed = urlsplit(service_url)
            fragment = urlencode({"pairing_handle": handle, "pairing_token": token, "expires": int(expires)})
            self._items[handle] = _Transaction(handle, hashlib.sha256(token.encode()).digest(), expires, private)
            return PairingOffer(handle, token, urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment)), expires, b64(public))

    def reset(self) -> None:
        with self._lock:
            self._items.clear()

    def begin(self, *, handle: str, token: str) -> PairingChallenge:
        with self._lock:
            item = self._valid(handle, token)
            item.challenge = item.challenge or secrets.token_bytes(32)
            public = item.server_private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            return PairingChallenge(handle, b64(item.challenge), b64(public), item.expires_at_epoch)

    def complete(self, *, handle: str, token: str, challenge_b64: str, phone_public_key_b64: str,
                 device_signing_public_key_b64: str, client_confirmation_b64: str) -> PairingResult:
        with self._lock:
            item = self._valid(handle, token)
            if item.challenge is None: raise PairingError("pairing challenge was not issued")
            try:
                challenge = unb64(challenge_b64); phone_raw = unb64(phone_public_key_b64); signing_raw = unb64(device_signing_public_key_b64)
                phone_public = X25519PublicKey.from_public_bytes(phone_raw)
                if len(signing_raw) != 32: raise ValueError
            except (ValueError, TypeError) as exc: raise PairingError("invalid pairing key material") from exc
            if not hmac.compare_digest(challenge, item.challenge): raise PairingError("pairing challenge mismatch")
            shared = item.server_private_key.exchange(phone_public)
            key = confirmation_key(shared)
            expected = hmac.new(key, b"tracepulse/client-confirmation/v1|" + challenge, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, unb64(client_confirmation_b64)): raise PairingError("client key confirmation failed")
            server_confirmation = hmac.new(key, b"tracepulse/server-confirmation/v1|" + challenge, hashlib.sha256).digest()
            server_public = item.server_private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            del self._items[handle]
            return PairingResult(handle, shared, challenge_b64, b64(server_confirmation), phone_public_key_b64, device_signing_public_key_b64, b64(server_public))

    def _valid(self, handle: str, token: str) -> _Transaction:
        item = self._items.get(handle)
        if item is None: raise PairingError("unknown or already-used pairing transaction")
        if time.time() >= item.expires_at_epoch: del self._items[handle]; raise PairingError("pairing transaction expired")
        if not hmac.compare_digest(item.token_hash, hashlib.sha256(token.encode()).digest()): raise PairingError("invalid pairing token")
        return item

    def _purge(self) -> None:
        now = time.time()
        for handle, item in list(self._items.items()):
            if now >= item.expires_at_epoch: del self._items[handle]