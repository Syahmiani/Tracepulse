from __future__ import annotations
import json
from flask import Blueprint, current_app, jsonify, request
from ..sensors.heartbeat import HeartbeatMonitor

bp = Blueprint("heartbeat_api", __name__, url_prefix="/api/heartbeat")

def ext(name):
    value = current_app.extensions.get(name)
    if value is None:
        raise RuntimeError(f"missing extension: {name}")
    return value

def error(message, status):
    return jsonify({"error": message}), status

def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value

@bp.post("/record")
def record_heartbeat():
    try:
        monitor = ext("tracepulse_heartbeat")
        data = body()
        monitor.record(
            sequence=data.get("sequence", 0),
            payload_size_bytes=data.get("payload_size_bytes", 0),
            received_monotonic=data.get("received_monotonic", 0.0)
        )
        return jsonify({"status": "recorded"}), 200
    except Exception:
        return error("heartbeat recording failed", 503)

@bp.get("/status")
def heartbeat_status():
    try:
        monitor = ext("tracepulse_heartbeat")
        return jsonify({
            "age_seconds": monitor.age_seconds(),
            "expired": monitor.expired(),
            "received_count": monitor.received_count
        })
    except Exception:
        return error("heartbeat status unavailable", 503)