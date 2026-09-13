from __future__ import annotations
import json
from flask import Blueprint, current_app, jsonify, request
from ..storage.audit_log import AuditLog
from ..storage.database import DatabaseError

bp = Blueprint("audit_api", __name__, url_prefix="/api/audit")

def ext(name):
    value = current_app.extensions.get(name)
    if value is None:
        raise RuntimeError(f"missing extension: {name}")
    return value

def error(message, status):
    return jsonify({"error": message}), status

@bp.get("/verify")
def verify_audit_chain():
    try:
        audit = ext("tracepulse_audit")
        return jsonify({"valid": audit.verify()})
    except Exception:
        return error("audit verification failed", 503)

@bp.get("/events")
def list_events():
    try:
        db = ext("tracepulse_db")
        audit = AuditLog(db)
        events = audit.db.fetch_all("SELECT * FROM security_events ORDER BY id DESC LIMIT 50")
        return jsonify({"events": events})
    except DatabaseError:
        return error("audit events unavailable", 503)