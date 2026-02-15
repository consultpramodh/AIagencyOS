.PHONY: setup migrate seed test run demo demo-m2 demo-full

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

migrate:
	. .venv/bin/activate && alembic upgrade head

seed:
	. .venv/bin/activate && python scripts/seed.py

test:
	. .venv/bin/activate && pytest -q

run:
	. .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

demo:
	. .venv/bin/activate && python scripts/demo_m1.py

demo-m2:
	. .venv/bin/activate && python scripts/demo_m2.py

demo-full:
	. .venv/bin/activate && python scripts/demo_full.py
