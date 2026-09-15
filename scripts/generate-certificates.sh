#!/usr/bin/env bash
set -euo pipefail
out="$(dirname "${BASH_SOURCE[0]}")/../config/tls"; mkdir -p "$out"; chmod 700 "$out"
cert_ip="${TRACEPULSE_CERT_IP:-192.168.0.152}"
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=TracePulse local CA" -keyout "$out/ca.key" -out "$out/ca.crt"
printf 'subjectAltName=IP:%s,IP:127.0.0.1,DNS:localhost\nextendedKeyUsage=serverAuth\n' "$cert_ip" > "$out/server.ext"
openssl req -new -newkey rsa:2048 -nodes -subj "/CN=TracePulse" -keyout "$out/server.key" -out "$out/server.csr"
openssl x509 -req -days 825 -in "$out/server.csr" -CA "$out/ca.crt" -CAkey "$out/ca.key" -CAcreateserial -out "$out/server.crt" -extfile "$out/server.ext"
chmod 600 "$out"/*.key; chmod 644 "$out"/*.crt