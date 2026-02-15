# M1 Demo Script (3 minutes)

## Option A: one command

- `./scripts/bootstrap.sh`

## Option B: step-by-step

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `alembic upgrade head`
4. `python scripts/seed.py`
5. `python scripts/demo_m1.py`
6. `uvicorn app.main:app --reload`
7. Open [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
8. Login as `owner@demo.local` / `demo1234`

Expected demo checks from `scripts/demo_m1.py`:

- Owner login succeeds (303 redirect)
- Owner can open tenant dashboard (200)
- Owner can create client (303)
- Viewer cross-tenant access is denied (403)
