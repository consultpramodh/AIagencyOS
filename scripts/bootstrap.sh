#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed.py
python scripts/demo_full.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
