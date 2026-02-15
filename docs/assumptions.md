# Assumptions

- [ASSUMPTION] M1 will use server-rendered FastAPI + Jinja2 to keep complexity low and ensure quick delivery for solo-founder workflows.
- [ASSUMPTION] Session-cookie auth is acceptable for M1; JWT can be introduced later if mobile/API-first patterns require it.
- [ASSUMPTION] SQLite is allowed for local development; Postgres is enabled via `DATABASE_URL` for deployment.
- [ASSUMPTION] Owner/admin roles can create tenant-scoped clients/projects in M1; viewer is read-only.
- [ASSUMPTION] Jobs panel in M1 uses tenant-scoped SSE heartbeat demo and will connect to real queued jobs in M4.
- [ASSUMPTION] M2 attachments use tenant-scoped local filesystem paths (`data/uploads/tenant_<id>/...`) for MVP; object storage can replace this in later milestones.
- [ASSUMPTION] Workflow execution in M4 uses a lightweight thread-based worker over a DB-backed job table for MVP; can be replaced by Celery/RQ later.
- [ASSUMPTION] Brainstorm mode defaults to deterministic heuristics and logs outputs as `AIOutput` even without paid LLM usage.
- [ASSUMPTION] Mobile companion in M7 is delivered as responsive mobile web routes (`/m`) rather than native mobile binaries.
- [ASSUMPTION] Marketing campaign recommendations are heuristic defaults (platform + objective + budget + days + client-name keyword expansion), and final launch settings remain human-approved before execution.
- [ASSUMPTION] “Most used templates across the world” are represented as commonly used operational patterns inferred from cross-market ad practice, not platform-provided global usage statistics.
