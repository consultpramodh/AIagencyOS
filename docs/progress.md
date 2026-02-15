# Build Progress

## Milestone Status

- [x] M1 — SaaS Foundation
- [x] M2 — Clients/Projects + Notes/Tasks (Notion-lite)
- [x] M3 — CRM-lite
- [x] M4 — Workflows + Runner + Jobs + Live Progress
- [x] M5 — Brainstorm → Agent mapping → Workflow creation
- [x] M6 — Integrations framework (stubs)
- [x] M7 — Mobile companion

## M1 Delivered

- FastAPI app scaffold with Jinja UI and tenant-aware navigation
- Auth with email/password and signed session cookies
- Multi-tenant data model (tenants/users/memberships/clients/projects)
- Centralized authorization dependency enforcing tenant access and RBAC
- Alembic migration baseline
- Seed/admin scripts
- Tenant isolation tests and RBAC tests
- Jobs panel with tenant-scoped SSE stream (demo heartbeat)

## M2 Delivered

- Notes/Documents CRUD (Markdown text area with inline edit)
- Tasks with status lanes (todo/in-progress/done) and Today queue (due today/overdue)
- Tenant-scoped attachment upload/download on notes
- Expanded seed data with starter note + task
- M2 tests for note/task flows and tenant-scoped attachment boundaries

## M3 Delivered

- CRM-lite module with contacts, deal stages, deals pipeline, and activities
- Deal stage movement and deal-to-project linking
- Tenant-safe CRM endpoints and tests

## M4 Delivered

- Workflow template/step CRUD with step ordering and agent assignment
- Workflow run engine with DB-backed jobs, run steps, run logs
- Approval gates (`approve` policy) with resumable workflow completion
- Jobs panel and SSE stream backed by real run logs

## M5 Delivered

- Brainstorm sessions with heuristic question set
- Answer capture and recommendation generation (agent org + workflow draft + metrics)
- Recommendation persisted to AI outputs log
- One-click creation of editable workflow from recommendation

## M6 Delivered

- Connector framework with connector types, instances, credentials placeholder, and run history
- Manual-mode connector runs with tenant-scoped logging
- Starter connector types for Ads/Analytics/Email/Books

## M7 Delivered

- Mobile companion page (`/m`) for approvals, today queue, run status, quick notes
- Approval action available from mobile via workflow approval endpoint
- Mobile-first compact layout using shared responsive styles
