# Build Progress

## Milestone Status

- [x] M1 — SaaS Foundation
- [ ] M2 — Clients/Projects + Notes/Tasks (Notion-lite)
- [ ] M3 — CRM-lite
- [ ] M4 — Workflows + Runner + Jobs + Live Progress
- [ ] M5 — Brainstorm → Agent mapping → Workflow creation
- [ ] M6 — Integrations framework (stubs)
- [ ] M7 — Mobile companion

## M1 Delivered

- FastAPI app scaffold with Jinja UI and tenant-aware navigation
- Auth with email/password and signed session cookies
- Multi-tenant data model (tenants/users/memberships/clients/projects)
- Centralized authorization dependency enforcing tenant access and RBAC
- Alembic migration baseline
- Seed/admin scripts
- Tenant isolation tests and RBAC tests
- Jobs panel with tenant-scoped SSE stream (demo heartbeat)
