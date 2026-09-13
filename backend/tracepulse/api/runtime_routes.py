from __future__ import annotations
import json
from flask import Blueprint, current_app, jsonify, request
from ..decision_engine import DecisionEngine
from ..os_integration.lock_engine import LockEngine
from ..storage.database import DatabaseError

bp = Blueprint("runtime_api", __name__, url_prefix="/api/runtime")

def ext(name):
    value = current_app.extensions.get(name)
    if value is None:
        raise RuntimeError(f"missing extension: {name}")
    return value

def error(message, status):
    return jsonify({"error": message}), status

@bp.get("/decision")
def get_decision():
    try:
        engine = ext("tracepulse_decision")
        return jsonify({"decision": engine.get_decision()})
    except Exception:
        return error("decision unavailable", 503)

@bp.post("/lock")
def lock_system():
    try:
        lock_engine = ext("tracepulse_lock")
        result = lock_engine.lock_now(reason=request.json.get("reason", "system lock"))
        return jsonify({"status": "locked", "result": result.__dict__})
    except Exception:
        return error("lock failed", 503)