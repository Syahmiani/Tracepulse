# Threat Model

## Assets

1. Device proximity data
2. Network communication channels
3. User authentication credentials
4. Sensor data streams
5. AI model weights

## Threats

### T1: Bluetooth Tracking
- **Description**: Unauthorized tracking of devices via BLE advertising
- **Mitigation**: MAC address randomization, signal strength obfuscation

### T2: Network Sniffing
- **Description**: Eavesdropping on network communications
- **Mitigation**: TLS 1.3 encryption, certificate pinning

### T3: Replay Attacks
- **Description**: Reusing captured authentication messages
- **Mitigation**: Nonce-based replay guard with timestamp validation

### T4: AI Model Poisoning
- **Description**: Injecting malicious training data
- **Mitigation**: Model registry with integrity checks, sandboxed training

### T5: Physical Access
- **Description**: Unauthorized access to monitoring device
- **Mitigation**: Secure boot, encrypted storage, tamper detection

## Trust Boundaries

1. Device ↔ Monitor (BLE)
2. Monitor ↔ Backend (WebSocket/TLS)
3. Backend ↔ Database (internal network)
4. Backend ↔ AI Models (secure enclave)

## Data Flow Security

- All device communications use authenticated encryption
- Session keys rotated every 30 minutes
- Audit logs append-only with cryptographic chaining
- AI model updates verified via digital signatures