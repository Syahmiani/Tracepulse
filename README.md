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

- Python 3.11+
- Node.js 18+
- Android Studio (for Android build)

### Installation

1. Backend:
```bash
cd backend
pip install -r requirements.in
```

2. Frontend:
```bash
cd frontend
npm install
```

3. Start the backend server:
```bash
uvicorn tracepulse.app:app --reload
```

## Architecture

See [THREAT_MODEL.md](THREAT_MODEL.md) for the security architecture.
