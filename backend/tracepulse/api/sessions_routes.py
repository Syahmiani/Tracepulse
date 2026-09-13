from __future__ import annotations
import json
from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify, request
from ..security.sessions import SessionManager, SessionError
from ..storage.database import DatabaseError

bp = Blueprint("sessions_api", __name__, url_prefix="/api/sessions")

def ext(name):
    value = current_app.extensions.get(name)
    if value is None:
        raise RuntimeError(f"missing extension: {name}")
    return value

def body():
    if not request.is_json or not isinstance(request.get_json(silent=True), dict):
        raise ValueError("JSON object required")
    return request.get_json()

def string(value, name, max_length=512):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"invalid {name}")
    return value.strip()

def error(message, status):
    return jsonify({"error": message}), status

@bp.get("/")
def list_sessions():
    try:
        manager = ext("tracepulse_sessions")
        active = manager.active()
        return jsonify({
            "active": {
                "session_id": active.session_id,
                "device_label": active.device_label,
                "status": str(active.status),
                "created_at_epoch": active.created_at_epoch,
                "last_seen_epoch": active.last_seen_epoch
            } if active else None
        })
    except Exception:
        return error("sessions unavailable", 503)

@bp.post("/revoke")
def revoke_session():
    try:
        manager = ext("tracepulse_sessions")
        manager.revoke(reason="client request")
        return jsonify({"status": "revoked"}), 200
    except SessionError as e:
        return error(str(e), 400)
    except Exception:
        return error("revocation failed", 503)