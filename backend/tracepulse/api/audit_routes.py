from __future__ import annotations
import json
from flask import Blueprint, current_app, jsonify, request
from ..storage.audit_log import AuditLog
from ..storage.database import DatabaseError

bp = Blueprint("audit_api", __name__, url_prefix="/api/audit")

def services():
    value = current_app.extensions.get("tracepulse_runtime")
    if value is None:
        raise RuntimeError("missing extension: tracepulse_runtime")
    return value

def error(message, status):
    return jsonify({"error": message}), status

@bp.get("/verify")
def verify_audit_chain():
    try:
        audit = services().audit
        return jsonify({"valid": audit.verify()})
    except Exception:
        return error("audit verification failed", 503)

@bp.get("/events")
def list_events():
    try:
        db = services().db
        audit = AuditLog(db)
        rows = audit.db.fetch_all("SELECT * FROM security_events ORDER BY id DESC LIMIT 50")
        events = [dict(row) for row in rows]
        return jsonify({"events": events})
    except DatabaseError:
        return error("audit events unavailable", 503)