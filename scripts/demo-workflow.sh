#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"
python_bin="$backend_dir/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
	echo "Backend virtual environment is missing. Run ./scripts/setup-kali.sh first." >&2
	exit 2
fi
if [[ ! -x "$frontend_dir/node_modules/.bin/vite" ]]; then
	echo "Frontend dependencies are missing. Run (cd frontend && npm install) first." >&2
	exit 2
fi

lan_ip="${TRACEPULSE_DEMO_IP:-$(hostname -I | awk '{print $1}')}"
lan_ip="${lan_ip:-127.0.0.1}"
export TRACEPULSE_BIND_HOST="${TRACEPULSE_BIND_HOST:-0.0.0.0}"
export TRACEPULSE_SERVICE_URL="${TRACEPULSE_SERVICE_URL:-https://$lan_ip:8443/}"
export TRACEPULSE_CERT_IP="${TRACEPULSE_CERT_IP:-$lan_ip}"
export TRACEPULSE_TLS_CERT="${TRACEPULSE_TLS_CERT:-$repo_root/config/tls/server.crt}"
export TRACEPULSE_TLS_KEY="${TRACEPULSE_TLS_KEY:-$repo_root/config/tls/server.key}"
export TRACEPULSE_LOCAL_STATUS_ONLY="${TRACEPULSE_LOCAL_STATUS_ONLY:-false}"
export TRACEPULSE_LOCAL_ADMIN_ONLY="${TRACEPULSE_LOCAL_ADMIN_ONLY:-false}"
export VITE_DEV_HTTPS=true
export VITE_DEV_TLS_CERT="$TRACEPULSE_TLS_CERT"
export VITE_DEV_TLS_KEY="$TRACEPULSE_TLS_KEY"
export TRACEPULSE_FRONTEND_ORIGIN="https://$lan_ip:5173"

if [[ ! -f "$TRACEPULSE_TLS_CERT" || ! -f "$TRACEPULSE_TLS_KEY" ]]; then
	"$repo_root/scripts/generate-certificates.sh"
fi

backend_pid=""
frontend_pid=""
cleanup() {
	[[ -n "$backend_pid" ]] && kill "$backend_pid" 2>/dev/null || true
	[[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
	cd "$backend_dir"
	"$repo_root/scripts/start-dev.sh"
) &
backend_pid=$!

(
	cd "$frontend_dir"
	npm run dev -- --host "${TRACEPULSE_FRONTEND_HOST:-0.0.0.0}"
) &
frontend_pid=$!

for _ in {1..30}; do
	if curl -kfsS https://127.0.0.1:8443/api/status/health >/dev/null 2>&1 &&
		curl -kfsS https://127.0.0.1:5173 >/dev/null 2>&1; then
		echo "TracePulse demo is ready."
		echo "Open this on the Kali laptop: https://$lan_ip:5173"
		echo "Scan the QR shown there with the phone camera, then keep the phone on the paired dashboard."
		echo "Pairing service: https://$lan_ip:8443"
		echo
		echo "The website will request and display the pairing QR automatically."
		echo
		if [[ "${TRACEPULSE_OPEN_BROWSER:-true}" == "true" ]]; then
			if command -v chromium >/dev/null 2>&1; then
				chromium --ignore-certificate-errors "https://$lan_ip:5173" >/dev/null 2>&1 &
			elif command -v xdg-open >/dev/null 2>&1; then
				xdg-open "https://$lan_ip:5173" >/dev/null 2>&1 &
			fi
			echo "Opened the TracePulse dashboard in the default browser."
		fi
		echo "Press Ctrl+C to stop both servers."
		wait
		exit 0
	fi
	sleep 1
done

echo "Demo services did not become ready within 30 seconds." >&2
exit 1
