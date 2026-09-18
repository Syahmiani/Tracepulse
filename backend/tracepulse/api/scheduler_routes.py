from __future__ import annotations
import ipaddress
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("scheduler_api", __name__, url_prefix="/api/scheduler")


def local():
    if current_app.config.get("TRACEPULSE_LOCAL_ADMIN_ONLY", True):
        try:
            ok = ipaddress.ip_address(request.remote_addr or "").is_loopback
        except ValueError:
            ok = False
        if not ok:
            raise PermissionError("scheduler is local-only")


def scheduler():
    return current_app.extensions["tracepulse_scheduler"]


@bp.get("")
def list_schedules():
    try:
        local()
        return jsonify({"schedules": [s.as_dict() for s in scheduler().list()]})
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@bp.post("")
def add_schedule():
    try:
        local()
        value = request.get_json(silent=True) or {}
        created = scheduler().add(
            label=str(value.get("label", "")),
            start=str(value.get("start", "")),
            end=str(value.get("end", "")),
            days=value.get("days", ()),
        )
        return jsonify(created.as_dict()), 201
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.delete("/<schedule_id>")
def delete_schedule(schedule_id):
    try:
        local()
        removed = scheduler().remove(schedule_id)
        if not removed:
            return jsonify({"error": "schedule not found"}), 404
        return jsonify({"status": "removed", "schedule_id": schedule_id})
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
