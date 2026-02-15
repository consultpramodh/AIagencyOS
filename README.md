# AI Marketing Agency OS

M1 foundation for a multi-tenant SaaS using FastAPI, Jinja2, SQLAlchemy, and Alembic.

## One-command local run

```bash
./scripts/bootstrap.sh
```

## Manual quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login).

## Demo Credentials

- `owner@demo.local` / `demo1234`
- `viewer@demo.local` / `demo1234`

## Environment Variables

- `DATABASE_URL` (default: `sqlite:///./agency_os.db`)
- `SECRET_KEY` (default dev key, set in production)

## Deploy (Render/Railway/Fly)

1. Provision Postgres.
2. Set `DATABASE_URL` and `SECRET_KEY`.
3. Start command:
   - `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Seed once (optional):
   - `python scripts/seed.py`

## Commands

```bash
make setup
make migrate
make seed
make test
make demo
make run
```

## Tests

```bash
pytest -q
```
