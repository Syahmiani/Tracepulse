# TracePulse

**Bluetooth & Network Security Monitor**

TracePulse is a comprehensive security monitoring platform that combines Bluetooth device tracking, network analysis, and AI-powered threat detection.

## Features

- Real-time Bluetooth device proximity detection
- Network packet capture and analysis
- AI-powered threat classification
- Secure device pairing
- End-to-end encrypted communications

## Getting Started

### Prerequisites

- Python 3.11-3.13 (`python3.13` is available on this Kali host)
- Node.js 18+
- Android Studio (for Android build)

### Installation

1. Backend:
```bash
./scripts/setup-kali.sh
```

2. Frontend:
```bash
cd frontend
npm install
```

3. Start the backend server:
```bash
cd ..
export TRACEPULSE_TLS_CERT="$PWD/config/tls/server.crt"
export TRACEPULSE_TLS_KEY="$PWD/config/tls/server.key"
./scripts/generate-certificates.sh
./scripts/start-dev.sh
```

In a second Kali terminal, create the one-time pairing QR:

```bash
cd ~/Tracepulse
./backend/.venv/bin/python scripts/create-pairing-qr.py
```

Build the Android APK with the compatible JDK:

```bash
sudo apt update && sudo apt install -y openjdk-21-jdk
./scripts/build-android.sh
```

### Demo workflow

Use two Kali terminals:

1. In terminal 1, start the complete demo:

```bash
./scripts/demo-workflow.sh
```

2. In terminal 2, open the HTTPS URL printed by the script on the Kali laptop.

The script starts the backend and HTTPS frontend, detects the Kali LAN address, and prints the URL to open. The local TracePulse website requests a one-time HTTPS pairing offer and displays its QR code. Scan that QR with the phone camera, accept the certificate warning if prompted, and leave the phone on the paired dashboard. The laptop switches to its paired dashboard automatically. Test the phone heartbeat, phone lock, phone unlock challenge, laptop lock, status cards, event log, and unpair controls, then press `Ctrl+C` in terminal 1 to end the demo. The script stops both services together.

The backend advertises `https://192.168.0.152:8443/` and binds to the current bridged Kali address. Set `TRACEPULSE_SERVICE_URL`, `TRACEPULSE_BIND_HOST`, and `TRACEPULSE_CERT_IP` if the address changes. BLE scanning uses adapter `hci0` and service UUID `7f5c6e7a-2f8a-4f3d-9a6b-1c0e8d4b2f91`. Status is available to the LAN for the Android client; pairing offer creation remains local-only, while pairing completion can be performed by the phone using the QR payload.

The laptop view is the monitoring console: it shows both endpoint identities (IP, MAC when available, hostname/user, device label), phone heartbeat/link health, the RSSI-derived perimeter distance and 8-meter boundary, lock delay, decision-engine state, OS session state, audit integrity, and the security event stream. The phone view remains the executor for heartbeat, lock, and credential-authorized unlock actions. Phone MAC discovery depends on the Kali host having a neighbor-table entry; browser clients cannot expose their MAC directly.

Proximity locking is configured for an 8-meter RSSI-estimated boundary and a 5-second continuous out-of-range delay before the workstation is locked. The distance estimate uses a 1-meter reference RSSI of -59 dBm and path-loss exponent 2.0; walls, orientation, and radio interference can affect the estimate.

## Architecture

See [THREAT_MODEL.md](THREAT_MODEL.md) for the security architecture.
