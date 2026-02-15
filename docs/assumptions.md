# Assumptions

- [ASSUMPTION] M1 will use server-rendered FastAPI + Jinja2 to keep complexity low and ensure quick delivery for solo-founder workflows.
- [ASSUMPTION] Session-cookie auth is acceptable for M1; JWT can be introduced later if mobile/API-first patterns require it.
- [ASSUMPTION] SQLite is allowed for local development; Postgres is enabled via `DATABASE_URL` for deployment.
- [ASSUMPTION] Owner/admin roles can create tenant-scoped clients/projects in M1; viewer is read-only.
- [ASSUMPTION] Jobs panel in M1 uses tenant-scoped SSE heartbeat demo and will connect to real queued jobs in M4.
