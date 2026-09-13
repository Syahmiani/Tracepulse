from __future__ import annotations
import json
from flask import Blueprint, current_app, jsonify, request
from ..storage.database import DatabaseError

bp = Blueprint("db_api", __name__, url_prefix="/api/db")

def ext(name):
    value = current_app.extensions.get(name)
    if value is None:
        raise RuntimeError(f"missing extension: {name}")
    return value

def body():
    if not request.is_json or not isinstance(request.get_json(silent=True), dict):
        raise ValueError("JSON object required")
    return request.get_json()

def error(message, status):
    return jsonify({"error": message}), status

@bp.get("/schema")
def get_schema():
    try:
        db = ext("tracepulse_db")
        schema = db.schema()
        return jsonify({"schema": schema})
    except DatabaseError:
        return error("database schema unavailable", 503)

@bp.get("/status")
def db_status():
    try:
        db = ext("tracepulse_db")
        return jsonify({"status": "healthy", "tables": db.list_tables()})
    except DatabaseError:
        return error("database status unavailable", 503)