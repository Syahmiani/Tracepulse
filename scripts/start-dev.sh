#!/usr/bin/env bash
set -euo pipefail
: "${TRACEPULSE_TLS_CERT:?set TRACEPULSE_TLS_CERT}"
: "${TRACEPULSE_TLS_KEY:?set TRACEPULSE_TLS_KEY}"
export TRACEPULSE_SERVICE_URL="${TRACEPULSE_SERVICE_URL:-https://127.0.0.1:8443/}"
case "$TRACEPULSE_SERVICE_URL" in https://*) ;; *) echo "HTTPS is required" >&2; exit 2 ;; esac
exec python -m tracepulse.app