#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/backend"
: "${TRACEPULSE_TLS_CERT:?set TRACEPULSE_TLS_CERT}"
: "${TRACEPULSE_TLS_KEY:?set TRACEPULSE_TLS_KEY}"
python_bin="$repo_root/backend/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
	python_bin="python3.13"
fi
export TRACEPULSE_BIND_HOST="${TRACEPULSE_BIND_HOST:-0.0.0.0}"
export TRACEPULSE_SERVICE_URL="${TRACEPULSE_SERVICE_URL:-https://192.168.0.152:8443/}"
export TRACEPULSE_BLE_SERVICE_UUID="${TRACEPULSE_BLE_SERVICE_UUID:-7f5c6e7a-2f8a-4f3d-9a6b-1c0e8d4b2f91}"
export TRACEPULSE_BLE_ADAPTER="${TRACEPULSE_BLE_ADAPTER:-hci0}"
export TRACEPULSE_PROXIMITY_DISTANCE_METERS="${TRACEPULSE_PROXIMITY_DISTANCE_METERS:-8.0}"
export TRACEPULSE_PROXIMITY_LOCK_DELAY_SECONDS="${TRACEPULSE_PROXIMITY_LOCK_DELAY_SECONDS:-5.0}"
export TRACEPULSE_LOCAL_STATUS_ONLY="${TRACEPULSE_LOCAL_STATUS_ONLY:-false}"
case "$TRACEPULSE_SERVICE_URL" in https://*) ;; *) echo "HTTPS is required" >&2; exit 2 ;; esac
exec "$python_bin" -m tracepulse.app