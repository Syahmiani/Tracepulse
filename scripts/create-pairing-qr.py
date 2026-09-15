#!/usr/bin/env python3
import json
import os
import ssl
import sys
from urllib.request import Request, urlopen

try:
    import qrcode
except ImportError as exc:
    raise SystemExit("qrcode is missing; run ./scripts/setup-kali.sh") from exc


def main():
    endpoint = os.getenv("TRACEPULSE_LOCAL_URL", "https://127.0.0.1:8443") + "/api/pairing/offer"
    request = Request(endpoint, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    context = ssl._create_unverified_context()
    with urlopen(request, context=context, timeout=10) as response:
        offer = json.load(response)
    payload = offer["qr_payload"]
    qr = qrcode.QRCode(border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    print("Scan this TracePulse pairing QR within 120 seconds:")
    for row in qr.get_matrix():
        print("".join("██" if cell else "  " for cell in row))
    print("\nPairing URL (fallback):")
    print(payload)


if __name__ == "__main__":
    main()