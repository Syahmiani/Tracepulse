#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pip-tools
python -m pip install --require-hashes -r requirements.lock.txt
python -m pip install -e . --no-deps