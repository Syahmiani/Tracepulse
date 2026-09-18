import base64
import hmac
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from tracepulse.app import create_app


def _decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_windows_http_pair_approve_and_unpair(tmp_path):
    app = create_app({
        "TESTING": True,
        "TRACEPULSE_SERVICE_URL": "http://127.0.0.1:8443/",
        "TRACEPULSE_ALLOW_INSECURE_LOCAL": True,
        "TRACEPULSE_LOCAL_ADMIN_ONLY": False,
        "TRACEPULSE_LOCAL_STATUS_ONLY": False,
        "TRACEPULSE_LOCK_OPERATIONS_ENABLED": False,
        "TRACEPULSE_DATABASE_PATH": str(tmp_path / "tracepulse.sqlite3"),
    })
    client = app.test_client()

    prepared = client.post("/api/pairing/prepare", json={})
    assert prepared.status_code == 201
    fragment = parse_qs(urlsplit(prepared.json["qr_payload"]).fragment)
    handle, token = fragment["pairing_handle"][0], fragment["pairing_token"][0]

    challenge_response = client.post("/api/pairing/begin", json={"handle": handle, "token": token})
    assert challenge_response.status_code == 200
    challenge = _decode(challenge_response.json["challenge_b64"])
    server_public = X25519PublicKey.from_public_bytes(_decode(challenge_response.json["server_public_key_b64"]))
    phone_private = X25519PrivateKey.generate()
    shared = phone_private.exchange(server_public)
    confirmation_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"tracepulse/pairing-confirmation/v1").derive(shared)
    confirmation = hmac.new(confirmation_key, b"tracepulse/client-confirmation/v1|" + challenge, "sha256").digest()
    signing_public = Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    completed = client.post("/api/pairing/complete", json={
        "handle": handle,
        "token": token,
        "challenge_b64": challenge_response.json["challenge_b64"],
        "phone_public_key_b64": base64.urlsafe_b64encode(phone_private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode().rstrip("="),
        "device_signing_public_key_b64": base64.urlsafe_b64encode(signing_public).decode().rstrip("="),
        "client_confirmation_b64": base64.urlsafe_b64encode(confirmation).decode().rstrip("="),
        "device_label": "Windows pairing test phone",
        "device_model": "browser",
    })
    assert completed.status_code == 201
    assert client.post("/api/pairing/approve", json={}).status_code == 200
    assert client.get("/api/status").json["session"]["approved"] is True

    duplicate = client.post("/api/pairing/prepare", json={})
    assert duplicate.status_code == 409
    assert client.post("/api/pairing/reset", json={}).status_code == 200
    assert client.get("/api/status").json["session"]["active"] is False
