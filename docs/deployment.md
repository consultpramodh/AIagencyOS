# Deployment

This app is a FastAPI server with Jinja templates, static assets, SQLAlchemy, and Alembic migrations. The preferred host is a Python web-service platform such as Render, Railway, or Fly.io.

Vercel can run this version through the included Python serverless adapter in `api/index.py`, but background jobs, local file persistence, and long-running tasks should move to a worker/web-service host as the product matures.

## Recommended MVP Setup

- Web app: Render
- Database: Supabase Postgres
- Auth/session secret: `SECRET_KEY`
- Local development: SQLite or Supabase local

## Vercel Setup

The repo includes `vercel.json` and `api/index.py` so the FastAPI app can deploy to Vercel.

Required Vercel environment variables:

```bash
DATABASE_URL=postgresql://...
SECRET_KEY=...
UPLOAD_ROOT=/tmp/uploads
```

Run migrations before or during deployment from a trusted machine:

```bash
DATABASE_URL=postgresql://... alembic upgrade head
```

## Required Environment Variables

```bash
DATABASE_URL=postgresql://...
SECRET_KEY=...
UPLOAD_ROOT=data/uploads
```

Use the Supabase Postgres connection string, not only the Supabase project URL. The project URL looks like `https://<project-ref>.supabase.co`; the database URL is available in Supabase under database connection settings and includes a password.

## Render Deploy

1. Create a new Render web service from the GitHub repo.
2. Use the included `render.yaml` blueprint, or configure manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set `DATABASE_URL` to the Supabase Postgres connection string.
4. Set `SECRET_KEY` to a long random value.
5. Deploy.

Seed demo data only when needed:

```bash
python scripts/seed.py
```

Do not run the seed script automatically in production after the first setup.

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/login`.
