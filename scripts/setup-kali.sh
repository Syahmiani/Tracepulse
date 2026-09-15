#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pip-tools
python -m pip install -r requirements.in
python -m pip install -e . --no-deps