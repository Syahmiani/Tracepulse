from __future__ import annotations
import json
from flask import Blueprint, current_app, jsonify, request
from ..decision_engine import DecisionEngine
from ..os_integration.lock_engine import LockEngine

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
        runtime = ext("tracepulse_runtime")
        return jsonify(runtime.decision_snapshot())
    except Exception:
        return error("decision unavailable", 503)

@bp.post("/lock")
def lock_system():
    try:
        runtime = ext("tracepulse_runtime")
        payload = request.get_json(silent=True) or {}
        result = runtime.lock_now(reason=payload.get("reason", "system lock"))
        return jsonify({"status": "locked", "result": result.__dict__})
    except Exception:
        return error("lock failed", 503)