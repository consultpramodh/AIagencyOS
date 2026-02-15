import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import (
    Activity,
    Approval,
    ApprovalRequest,
    Attachment,
    ClientFinancial,
    CalendarEvent,
    Client,
    Contact,
    Deal,
    DealStage,
    Event,
    Job,
    Membership,
    Note,
    Project,
    ServiceJob,
    Task,
    WorkflowRun,
)
from app.services.authz import CurrentContext, require_context, require_role
from app.services.intelligence import HealthScore, audit_change, compute_client_health, emit_event
from app.services.storage import store_tenant_file

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _base_context(ctx: CurrentContext, db: Session) -> dict:
    memberships = db.query(Membership).filter(Membership.user_id == ctx.user.id).all()
    clients = db.query(Client).filter(Client.tenant_id == ctx.tenant.id).order_by(Client.id.asc()).all()
    projects = db.query(Project).filter(Project.tenant_id == ctx.tenant.id).order_by(Project.id.asc()).all()
    return {"ctx": ctx, "memberships": memberships, "clients": clients, "projects": projects}


def _today_tasks(ctx: CurrentContext, db: Session):
    today = date.today()
    return (
        db.query(Task)
        .filter(Task.tenant_id == ctx.tenant.id, Task.status != "done", Task.due_date.is_not(None), Task.due_date <= today)
        .order_by(Task.due_date.asc())
        .all()
    )


def _calendar_rows(ctx: CurrentContext, db: Session):
    tasks = db.query(Task).filter(Task.tenant_id == ctx.tenant.id).all()
    service_jobs = db.query(ServiceJob).filter(ServiceJob.tenant_id == ctx.tenant.id).all()
    calendar_events = db.query(CalendarEvent).filter(CalendarEvent.tenant_id == ctx.tenant.id).all()
    approvals = db.query(Approval).filter(Approval.tenant_id == ctx.tenant.id, Approval.status == "pending").all()
    today = date.today()
    horizon = today + timedelta(days=21)
    rows: list[tuple[date, str, str]] = []
    for t in tasks:
        if t.due_date and today <= t.due_date <= horizon:
            rows.append((t.due_date, "Task", t.title))
    for s in service_jobs:
        if s.scheduled_for and today <= s.scheduled_for <= horizon:
            rows.append((s.scheduled_for, "Service", f"{s.title} ({s.stage})"))
    for e in calendar_events:
        if today <= e.event_date <= horizon:
            rows.append((e.event_date, "Event", e.title))
    for a in approvals:
        day = a.created_at.date()
        if today <= day <= horizon:
            rows.append((day, "Approval", a.title))
    rows.sort(key=lambda x: x[0])
    return rows


def _dashboard_payload(ctx: CurrentContext, db: Session, mode: str = "admin", client_id: int | None = None) -> dict:
    if mode not in {"admin", "client"}:
        mode = "admin"
    base = _base_context(ctx, db)
    selected_client = None
    if mode == "client" and client_id is None and base["clients"]:
        client_id = base["clients"][0].id
    if mode == "client" and client_id:
        selected_client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
        if not selected_client:
            mode = "admin"

    today_tasks = _today_tasks(ctx, db)
    approvals_pending = db.query(Approval).filter(Approval.tenant_id == ctx.tenant.id, Approval.status == "pending").count()
    if approvals_pending == 0:
        approvals_pending = db.query(ApprovalRequest).filter(ApprovalRequest.tenant_id == ctx.tenant.id, ApprovalRequest.status == "pending").count()
    pending_approvals = db.query(Approval).filter(Approval.tenant_id == ctx.tenant.id, Approval.status == "pending").order_by(Approval.id.desc()).limit(8).all()
    recent_jobs = db.query(Job).filter(Job.tenant_id == ctx.tenant.id).order_by(Job.id.desc()).limit(6).all()
    recent_runs = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id).order_by(WorkflowRun.id.desc()).limit(8).all()
    blocked_runs = [r for r in recent_runs if r.status == "blocked"]
    failed_runs = [r for r in recent_runs if r.status == "failed"]

    active_deals = db.query(Deal).filter(Deal.tenant_id == ctx.tenant.id, Deal.status == "open").order_by(Deal.id.desc()).limit(10).all()
    upcoming_activities = (
        db.query(Activity)
        .filter(Activity.tenant_id == ctx.tenant.id, Activity.status == "open", Activity.due_date.is_not(None))
        .order_by(Activity.due_date.asc())
        .limit(8)
        .all()
    )

    decisions = [
        {
            "title": "Approvals waiting",
            "value": approvals_pending,
            "status": "BLOCKED" if approvals_pending else "PASS",
            "detail": "Pending approvals are pausing automation execution.",
            "cta": f"/workflows?tenant_id={ctx.tenant.id}",
            "cta_label": "Open approvals",
        },
        {
            "title": "Overdue tasks",
            "value": len(today_tasks),
            "status": "DUE" if today_tasks else "PASS",
            "detail": "Tasks due today or earlier need triage.",
            "cta": f"/tasks?tenant_id={ctx.tenant.id}",
            "cta_label": "Open tasks",
        },
        {
            "title": "Blocked runs",
            "value": len(blocked_runs),
            "status": "BLOCKED" if blocked_runs else "PASS",
            "detail": "Blocked workflows require a decision to continue.",
            "cta": f"/workflows?tenant_id={ctx.tenant.id}",
            "cta_label": "Review runs",
        },
    ]

    contact_gap = [c for c in base["clients"] if not (c.contact_email or c.contact_phone)]
    threats = [
        {
            "title": "Failed workflows",
            "value": len(failed_runs),
            "status": "FAIL" if failed_runs else "PASS",
            "detail": "Any failed run can impact client delivery consistency.",
        },
        {
            "title": "Client contact gaps",
            "value": len(contact_gap),
            "status": "RISK" if contact_gap else "PASS",
            "detail": "Clients missing reachable contact channels increase response delays.",
        },
        {
            "title": "Job health",
            "value": len([j for j in recent_jobs if j.status == "failed"]),
            "status": "RISK" if any(j.status == "failed" for j in recent_jobs) else "PASS",
            "detail": "Failed jobs indicate system-level execution risks.",
        },
    ]

    opportunities = [
        {
            "title": "Open pipeline opportunities",
            "value": len(active_deals),
            "status": "PASS" if active_deals else "RISK",
            "detail": "Open deals are near-term revenue opportunities.",
            "cta": f"/crm?tenant_id={ctx.tenant.id}",
            "cta_label": "Open CRM",
        },
        {
            "title": "Upcoming client activities",
            "value": len(upcoming_activities),
            "status": "PASS" if upcoming_activities else "RISK",
            "detail": "Scheduled activities can unlock upsells and renewals.",
            "cta": f"/crm?tenant_id={ctx.tenant.id}",
            "cta_label": "View activities",
        },
        {
            "title": "Automation throughput",
            "value": len([r for r in recent_runs if r.status == "succeeded"]),
            "status": "PASS" if any(r.status == "succeeded" for r in recent_runs) else "RISK",
            "detail": "Successful runs free capacity for growth work.",
            "cta": f"/workflows?tenant_id={ctx.tenant.id}",
            "cta_label": "Inspect workflows",
        },
    ]

    blocked_count = len(blocked_runs)
    active_count = len([j for j in recent_jobs if j.status in {"running", "queued"}])

    financials = db.query(ClientFinancial).filter(ClientFinancial.tenant_id == ctx.tenant.id).all()
    mrr_total = sum(x.mrr_cents for x in financials)
    renewals_soon = sum(1 for x in financials if x.renewal_date and x.renewal_date <= date.today() + timedelta(days=30))
    pipeline_14d = sum(x.value_cents for x in db.query(Deal).filter(Deal.tenant_id == ctx.tenant.id, Deal.close_date.is_not(None), Deal.close_date <= date.today() + timedelta(days=14)).all())
    runs_last_24h = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.created_at >= datetime.utcnow() - timedelta(hours=24))
        .count()
    )

    health_by_client: dict[int, HealthScore] = {}
    for client in base["clients"]:
        health_by_client[client.id] = compute_client_health(db, ctx.tenant.id, client.id)
    at_risk_clients = len([x for x in health_by_client.values() if x.score >= 70])
    pulse_metrics = [
        {"label": "Approvals", "value": approvals_pending, "trend": "pending", "direction": "down" if approvals_pending else "flat"},
        {"label": "Due", "value": len(today_tasks), "trend": "today", "direction": "down" if today_tasks else "flat"},
        {"label": "Active", "value": active_count, "trend": "live", "direction": "up" if active_count else "flat"},
        {"label": "Blocked", "value": blocked_count, "trend": "gates", "direction": "down" if blocked_count else "flat"},
        {"label": "Risk", "value": at_risk_clients, "trend": "watch", "direction": "down" if at_risk_clients else "flat"},
        {"label": "AI Cost", "value": "$0.00", "trend": "month", "direction": "flat"},
    ]

    intelligence_items = []
    event_rows = db.query(Event).filter(Event.tenant_id == ctx.tenant.id).order_by(Event.created_at.desc()).limit(40).all()
    for ev in event_rows:
        kind = "info"
        if "failed" in ev.type:
            kind = "fail"
        elif "blocked" in ev.type:
            kind = "blocked"
        elif "approval" in ev.type:
            kind = "approval"
        elif "deal" in ev.type or "renewal" in ev.type or "financial" in ev.type:
            kind = "revenue"
        detail = ""
        try:
            detail_json = json.loads(ev.detail_json or "{}")
            detail = detail_json.get("detail", "")
        except Exception:
            detail = ""
        intelligence_items.append(
            {
                "kind": kind,
                "title": ev.title,
                "meta": ev.entity_type,
                "timestamp": ev.created_at.strftime("%Y-%m-%d %H:%M"),
                "detail": detail or "Open entity to inspect details.",
                "level": "risk" if ev.severity in {"high", "critical"} else "neutral",
            }
        )

    if not intelligence_items:
        intelligence_items = [
            {
                "kind": "empty",
                "title": "No critical alerts right now",
                "meta": "System is quiet",
                "timestamp": "recent",
                "detail": "Connect validations or run workflows to populate live intelligence.",
                "level": "good",
            }
        ]

    due_by_client: dict[int, int] = {}
    for task in today_tasks:
        if task.project_id:
            project = db.query(Project).filter(Project.id == task.project_id, Project.tenant_id == ctx.tenant.id).first()
            if project:
                due_by_client[project.client_id] = due_by_client.get(project.client_id, 0) + 1

    client_tiles = []
    for client in base["clients"]:
        approvals_for_client = db.query(Approval).filter(Approval.tenant_id == ctx.tenant.id, Approval.client_id == client.id, Approval.status == "pending").count()
        blocked_for_client = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.client_id == client.id, WorkflowRun.status == "blocked").count()
        due_for_client = due_by_client.get(client.id, 0)
        score = blocked_for_client * 5 + approvals_for_client * 3 + due_for_client * 2
        fin = next((f for f in financials if f.client_id == client.id), None)
        health = health_by_client.get(client.id)
        client_tiles.append(
            {
                "id": client.id,
                "name": client.name,
                "status": client.status,
                "contact_name": client.contact_name,
                "contact_email": client.contact_email,
                "contact_phone": client.contact_phone,
                "revenue": f"${fin.mrr_cents / 100:,.0f}" if fin and fin.mrr_cents else "—",
                "roas": "—",
                "risk": f"{health.risk_level} ({health.score})" if health else "—",
                "risk_score": health.score if health else 0,
                "risk_drivers": health.drivers if health else [],
                "workflows": db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.client_id == client.id).count(),
                "approvals": approvals_for_client,
                "due": due_for_client,
                "blocked": blocked_for_client,
                "pipeline_value": sum(
                    x.value_cents
                    for x in db.query(Deal).filter(Deal.tenant_id == ctx.tenant.id, Deal.client_id == client.id, Deal.status == "open").all()
                ),
                "score": score,
            }
        )
    client_tiles.sort(key=lambda x: (-x["score"], x["name"].lower()))

    macro_metrics = {
        "mrr_total": mrr_total,
        "pipeline_14d": pipeline_14d,
        "renewals_soon": renewals_soon,
        "automation_load": runs_last_24h,
    }

    if mode == "client" and selected_client:
        client_health = health_by_client.get(selected_client.id) or compute_client_health(db, ctx.tenant.id, selected_client.id)
        client_tasks = []
        for task in today_tasks:
            if task.client_id == selected_client.id:
                client_tasks.append(task)
                continue
            if task.project_id:
                p = db.query(Project).filter(Project.id == task.project_id, Project.tenant_id == ctx.tenant.id).first()
                if p and p.client_id == selected_client.id:
                    client_tasks.append(task)
        client_approvals = db.query(Approval).filter(Approval.tenant_id == ctx.tenant.id, Approval.client_id == selected_client.id, Approval.status == "pending").count()
        client_blocked = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.client_id == selected_client.id, WorkflowRun.status == "blocked").count()
        client_failed = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.client_id == selected_client.id, WorkflowRun.status == "failed").count()
        client_pipeline = sum(x.value_cents for x in db.query(Deal).filter(Deal.tenant_id == ctx.tenant.id, Deal.client_id == selected_client.id, Deal.status == "open").all())
        client_fin = db.query(ClientFinancial).filter(ClientFinancial.tenant_id == ctx.tenant.id, ClientFinancial.client_id == selected_client.id).first()
        decisions = [
            {
                "title": "Client approvals waiting",
                "value": client_approvals,
                "status": "BLOCKED" if client_approvals else "PASS",
                "detail": "Pending approvals for this client need decision.",
                "cta": f"/clients?tenant_id={ctx.tenant.id}&quick_client_id={selected_client.id}",
                "cta_label": "Open client",
            },
            {
                "title": "Client overdue tasks",
                "value": len(client_tasks),
                "status": "DUE" if client_tasks else "PASS",
                "detail": "Overdue tasks for this client.",
                "cta": f"/tasks?tenant_id={ctx.tenant.id}",
                "cta_label": "Open tasks",
            },
        ]
        threats = [
            {
                "title": "Blocked runs",
                "value": client_blocked,
                "status": "BLOCKED" if client_blocked else "PASS",
                "detail": "Blocked runs tied to this client.",
            },
            {
                "title": "Failed runs",
                "value": client_failed,
                "status": "FAIL" if client_failed else "PASS",
                "detail": "Recent failed runs tied to this client.",
            },
            {
                "title": "Risk score",
                "value": client_health.score,
                "status": "RISK" if client_health.score >= 40 else "PASS",
                "detail": ", ".join(client_health.drivers) if client_health.drivers else "No critical drivers.",
            },
        ]
        opportunities = [
            {
                "title": "Pipeline value",
                "value": f"${client_pipeline / 100:.2f}",
                "status": "PASS" if client_pipeline else "RISK",
                "detail": "Open pipeline for this client.",
                "cta": f"/crm?tenant_id={ctx.tenant.id}",
                "cta_label": "Open CRM",
            },
            {
                "title": "MRR",
                "value": f"${(client_fin.mrr_cents / 100):.2f}" if client_fin else "—",
                "status": "PASS" if client_fin and client_fin.mrr_cents else "RISK",
                "detail": "Client recurring monthly revenue.",
                "cta": f"/clients?tenant_id={ctx.tenant.id}",
                "cta_label": "Update financials",
            },
        ]
        pulse_metrics = [
            {"label": "Approvals", "value": client_approvals, "trend": "client", "direction": "down" if client_approvals else "flat"},
            {"label": "Due", "value": len(client_tasks), "trend": "client", "direction": "down" if client_tasks else "flat"},
            {"label": "Blocked", "value": client_blocked, "trend": "client", "direction": "down" if client_blocked else "flat"},
            {"label": "Risk", "value": client_health.score, "trend": "score", "direction": "down" if client_health.score >= 40 else "flat"},
        ]
        macro_metrics = {
            "mrr_total": client_fin.mrr_cents if client_fin else 0,
            "pipeline_14d": client_pipeline,
            "renewals_soon": 1 if client_fin and client_fin.renewal_date and client_fin.renewal_date <= date.today() + timedelta(days=30) else 0,
            "automation_load": db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.client_id == selected_client.id).count(),
        }
        client_tiles = [x for x in client_tiles if x["id"] == selected_client.id]
        event_rows = db.query(Event).filter(Event.tenant_id == ctx.tenant.id, Event.entity_type == "client", Event.entity_id == selected_client.id).order_by(Event.created_at.desc()).limit(20).all()
        if event_rows:
            intelligence_items = [
                {
                    "kind": "revenue" if "deal" in ev.type or "financial" in ev.type else ("approval" if "approval" in ev.type else "info"),
                    "title": ev.title,
                    "meta": ev.entity_type,
                    "timestamp": ev.created_at.strftime("%Y-%m-%d %H:%M"),
                    "detail": "Client-specific event",
                    "level": "neutral",
                }
                for ev in event_rows
            ]

    return {
        **base,
        "today_tasks": today_tasks,
        "calendar_rows": _calendar_rows(ctx, db)[:8],
        "approvals_pending": approvals_pending,
        "recent_jobs": recent_jobs,
        "recent_runs": recent_runs,
        "pulse_metrics": pulse_metrics,
        "intelligence_items": intelligence_items,
        "decisions": decisions,
        "threats": threats,
        "opportunities": opportunities,
        "client_tiles": client_tiles,
        "macro_metrics": macro_metrics,
        "current_mode": mode,
        "selected_client": selected_client,
    }


@router.get("/")
def home(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    mode = request.query_params.get("mode", "admin")
    client_id = request.query_params.get("client_id")
    parsed_client_id = int(client_id) if client_id and client_id.isdigit() else None
    return templates.TemplateResponse(request, "dashboard.html", _dashboard_payload(ctx, db, mode=mode, client_id=parsed_client_id))


@router.get("/dashboard")
def dashboard_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    mode = request.query_params.get("mode", "admin")
    client_id = request.query_params.get("client_id")
    parsed_client_id = int(client_id) if client_id and client_id.isdigit() else None
    return templates.TemplateResponse(request, "dashboard.html", _dashboard_payload(ctx, db, mode=mode, client_id=parsed_client_id))


@router.get("/search")
def search(
    q: str = Query(default="", min_length=0, max_length=80),
    ctx: CurrentContext = Depends(require_context),
    db: Session = Depends(get_db),
):
    q = q.strip()
    command_rows = [
        {"title": "Go to Dashboard", "url": f"/dashboard?tenant_id={ctx.tenant.id}"},
        {"title": "Go to Clients", "url": f"/clients?tenant_id={ctx.tenant.id}"},
        {"title": "Go to Calendar", "url": f"/calendar?tenant_id={ctx.tenant.id}"},
        {"title": "Go to Marketing", "url": f"/marketing?tenant_id={ctx.tenant.id}"},
        {"title": "New Campaign", "url": f"/marketing?tenant_id={ctx.tenant.id}&open=new-campaign"},
        {"title": "New Client", "url": f"/clients?tenant_id={ctx.tenant.id}&open=new-client"},
        {"title": "New Project", "url": f"/projects?tenant_id={ctx.tenant.id}&open=new-project"},
    ]
    if not q:
        return {"clients": [], "projects": [], "commands": command_rows, "results": [{"type": "command", **c} for c in command_rows]}

    like = f"%{q}%"
    clients_json: list[dict[str, str | int]] = []
    projects_json: list[dict[str, str | int]] = []

    clients = db.query(Client).filter(Client.tenant_id == ctx.tenant.id, Client.name.ilike(like)).order_by(Client.name.asc()).limit(8).all()
    for client in clients:
        clients_json.append({"id": client.id, "name": client.name, "url": f"/clients?tenant_id={ctx.tenant.id}&quick_client_id={client.id}"})

    projects = db.query(Project).filter(Project.tenant_id == ctx.tenant.id, Project.name.ilike(like)).order_by(Project.name.asc()).limit(8).all()
    for project in projects:
        client_name = db.query(Client).filter(Client.id == project.client_id, Client.tenant_id == ctx.tenant.id).first()
        projects_json.append(
            {
                "id": project.id,
                "name": project.name,
                "client_id": project.client_id,
                "client_name": client_name.name if client_name else "—",
                "url": f"/projects?tenant_id={ctx.tenant.id}",
            }
        )

    commands = [x for x in command_rows if q.lower() in x["title"].lower()]

    flattened = [{"type": "command", "title": c["title"], "subtitle": "Command", "url": c["url"]} for c in commands]
    flattened.extend([{"type": "client", "title": c["name"], "subtitle": "Client", "url": c["url"]} for c in clients_json])
    flattened.extend([{"type": "project", "title": p["name"], "subtitle": f"Project · {p['client_name']}", "url": p["url"]} for p in projects_json])

    return {"clients": clients_json, "projects": projects_json, "commands": commands, "results": flattened[:20]}


@router.get("/clients/{client_id}/quickview")
def client_quickview(client_id: int, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    approvals = db.query(Approval).filter(Approval.tenant_id == ctx.tenant.id, Approval.client_id == client.id, Approval.status == "pending").count()
    blocked = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id, WorkflowRun.client_id == client.id, WorkflowRun.status == "blocked").count()
    project_ids = [p.id for p in db.query(Project).filter(Project.tenant_id == ctx.tenant.id, Project.client_id == client.id).all()]
    due = 0
    if project_ids:
        due = db.query(Task).filter(Task.tenant_id == ctx.tenant.id, Task.project_id.in_(project_ids), Task.status != "done", Task.due_date.is_not(None), Task.due_date <= date.today()).count()

    health = compute_client_health(db, ctx.tenant.id, client.id)
    fin = db.query(ClientFinancial).filter(ClientFinancial.tenant_id == ctx.tenant.id, ClientFinancial.client_id == client.id).first()

    return {
        "id": client.id,
        "name": client.name,
        "status": client.status,
        "email": client.contact_email or None,
        "phone": client.contact_phone or None,
        "approvals": approvals,
        "blocked": blocked,
        "due": due,
        "risk_score": health.score,
        "risk_level": health.risk_level,
        "drivers": health.drivers,
        "mrr_cents": fin.mrr_cents if fin else 0,
        "open_client_url": f"/clients?tenant_id={ctx.tenant.id}",
        "open_projects_url": f"/projects?tenant_id={ctx.tenant.id}",
    }


@router.get("/operations")
def operations_hub(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    return templates.TemplateResponse(request, "operations.html", {**base, "today_tasks": _today_tasks(ctx, db)})


@router.get("/clients")
def clients_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    contacts = db.query(Contact).filter(Contact.tenant_id == ctx.tenant.id).order_by(Contact.created_at.desc()).all()
    contacts_by_client: dict[int, list[Contact]] = {}
    for contact in contacts:
        contacts_by_client.setdefault(contact.client_id, []).append(contact)
    financials = db.query(ClientFinancial).filter(ClientFinancial.tenant_id == ctx.tenant.id).all()
    fin_by_client = {f.client_id: f for f in financials}
    stages = db.query(DealStage).filter(DealStage.tenant_id == ctx.tenant.id).order_by(DealStage.position.asc()).all()
    if not stages:
        for i, name in enumerate(["Lead", "Qualified", "Proposal", "Won"], start=1):
            db.add(DealStage(tenant_id=ctx.tenant.id, name=name, position=i, is_won=name == "Won"))
        db.commit()
        stages = db.query(DealStage).filter(DealStage.tenant_id == ctx.tenant.id).order_by(DealStage.position.asc()).all()
    health_by_client = {c.id: compute_client_health(db, ctx.tenant.id, c.id) for c in base["clients"]}
    return templates.TemplateResponse(
        request,
        "clients.html",
        {**base, "contacts_by_client": contacts_by_client, "fin_by_client": fin_by_client, "deal_stages": stages, "health_by_client": health_by_client},
    )


@router.get("/projects")
def projects_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    return templates.TemplateResponse(request, "projects.html", base)


@router.get("/tasks")
def tasks_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    tasks = db.query(Task).filter(Task.tenant_id == ctx.tenant.id).order_by(Task.created_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {**base, "tasks_todo": [t for t in tasks if t.status == "todo"], "tasks_in_progress": [t for t in tasks if t.status == "in_progress"], "tasks_done": [t for t in tasks if t.status == "done"], "today_tasks": _today_tasks(ctx, db)},
    )


@router.get("/notes")
def notes_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    notes = db.query(Note).filter(Note.tenant_id == ctx.tenant.id).order_by(Note.updated_at.desc()).all()
    note_ids = [n.id for n in notes]
    attachments = {}
    if note_ids:
        rows = db.query(Attachment).filter(Attachment.tenant_id == ctx.tenant.id, Attachment.note_id.in_(note_ids)).all()
        for item in rows:
            attachments.setdefault(item.note_id, []).append(item)
    return templates.TemplateResponse(request, "notes.html", {**base, "notes": notes, "attachments": attachments})


@router.get("/scheduler")
def scheduler_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    service_jobs = db.query(ServiceJob).filter(ServiceJob.tenant_id == ctx.tenant.id).order_by(ServiceJob.created_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "scheduler.html",
        {
            **base,
            "service_intake": [s for s in service_jobs if s.stage == "intake"],
            "service_scheduled": [s for s in service_jobs if s.stage == "scheduled"],
            "service_in_service": [s for s in service_jobs if s.stage == "in_service"],
            "service_completed": [s for s in service_jobs if s.stage == "completed"],
        },
    )


@router.get("/calendar")
def calendar_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    rows = _calendar_rows(ctx, db)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    days = [week_start + timedelta(days=i) for i in range(7)]
    week_cells: list[dict[str, object]] = []
    for day in days:
        items = []
        for row in rows:
            if row[0] == day:
                decision_type = "review"
                if row[1] == "Service":
                    decision_type = "call"
                elif row[1] == "Event":
                    decision_type = "approval"
                items.append({"date": row[0], "kind": row[1], "title": row[2], "decision_type": decision_type})
        week_cells.append({"date": day, "label": day.strftime("%a"), "items": items})

    today_decisions = [r for r in rows if r[0] == today]
    priority = {"Approval": 0, "Task": 1, "Service": 2, "Event": 3}
    today_decisions.sort(key=lambda x: priority.get(x[1], 9))

    upcoming_rows = [r for r in rows if today <= r[0] <= today + timedelta(days=14)]

    return templates.TemplateResponse(
        request,
        "calendar.html",
        {
            **base,
            "calendar_rows": rows,
            "week_cells": week_cells,
            "today_decisions": today_decisions,
            "decision_types": ["approval", "call", "report", "review"],
            "upcoming_rows": upcoming_rows,
        },
    )


@router.post("/clients")
def create_client(
    name: str = Form(...),
    contact_name: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    website_url: str = Form(""),
    social_handles: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    db.add(
        Client(
            tenant_id=ctx.tenant.id,
            name=name.strip(),
            contact_name=contact_name.strip(),
            contact_email=contact_email.strip(),
            contact_phone=contact_phone.strip(),
            website_url=website_url.strip(),
            social_handles=social_handles.strip(),
        )
    )
    db.commit()
    return RedirectResponse(url=f"/clients?tenant_id={ctx.tenant.id}&toast=client-created", status_code=303)


@router.post("/clients/{client_id}/financials")
def upsert_client_financials(
    client_id: int,
    mrr_cents: int = Form(0),
    retainer_cents: int = Form(0),
    last_invoice_cents: int = Form(0),
    cogs_estimate_cents: int = Form(0),
    renewal_date: str | None = Form(None),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    parsed_renewal = _parse_date(renewal_date)
    fin = db.query(ClientFinancial).filter(ClientFinancial.tenant_id == ctx.tenant.id, ClientFinancial.client_id == client.id).first()
    before = {}
    if fin:
        before = {
            "mrr_cents": fin.mrr_cents,
            "retainer_cents": fin.retainer_cents,
            "last_invoice_cents": fin.last_invoice_cents,
            "cogs_estimate_cents": fin.cogs_estimate_cents,
            "renewal_date": fin.renewal_date.isoformat() if fin.renewal_date else None,
        }
    if not fin:
        fin = ClientFinancial(tenant_id=ctx.tenant.id, client_id=client.id)
        db.add(fin)
    fin.mrr_cents = max(0, mrr_cents)
    fin.retainer_cents = max(0, retainer_cents)
    fin.last_invoice_cents = max(0, last_invoice_cents)
    fin.cogs_estimate_cents = max(0, cogs_estimate_cents)
    fin.renewal_date = parsed_renewal
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="client_financials_updated",
        entity_type="client",
        entity_id=client.id,
        severity="info",
        title=f"Financials updated for {client.name}",
        detail={"detail": "MRR/retainer fields updated"},
    )
    audit_change(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        entity_type="client_financials",
        entity_id=client.id,
        action="upsert",
        before=before,
        after={
            "mrr_cents": fin.mrr_cents,
            "retainer_cents": fin.retainer_cents,
            "last_invoice_cents": fin.last_invoice_cents,
            "cogs_estimate_cents": fin.cogs_estimate_cents,
            "renewal_date": fin.renewal_date.isoformat() if fin.renewal_date else None,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/clients?tenant_id={ctx.tenant.id}&toast=financials-updated", status_code=303)


@router.post("/approvals")
def create_approval(
    client_id: int | None = Form(None),
    project_id: int | None = Form(None),
    title: str = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    row = Approval(
        tenant_id=ctx.tenant.id,
        client_id=client_id,
        project_id=project_id,
        workflow_run_id=None,
        status="pending",
        title=title.strip(),
        requested_by_user_id=ctx.user.id,
    )
    db.add(row)
    db.flush()
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="approval_pending",
        entity_type="approval",
        entity_id=row.id,
        severity="high",
        title=f"Approval pending: {row.title}",
        detail={"detail": "Approval pending blocks downstream step"},
    )
    db.commit()
    return RedirectResponse(url=f"/dashboard?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/projects")
def create_project(client_id: int = Form(...), name: str = Form(...), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if client:
        db.add(Project(tenant_id=ctx.tenant.id, client_id=client.id, name=name.strip()))
        db.commit()
    return RedirectResponse(url=f"/projects?tenant_id={ctx.tenant.id}&toast=project-created", status_code=303)


@router.post("/notes")
def create_note(title: str = Form(...), body_markdown: str = Form(""), project_id: int | None = Form(None), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Project access denied")
    db.add(Note(tenant_id=ctx.tenant.id, project_id=project_id, created_by_user_id=ctx.user.id, title=title.strip(), body_markdown=body_markdown.strip()))
    db.commit()
    return RedirectResponse(url=f"/notes?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/notes/{note_id}/update")
def update_note(note_id: int, title: str = Form(...), body_markdown: str = Form(""), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id, Note.tenant_id == ctx.tenant.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.title = title.strip()
    note.body_markdown = body_markdown.strip()
    db.commit()
    return RedirectResponse(url=f"/notes?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/notes/{note_id}/attachments")
def upload_attachment(note_id: int, file: UploadFile = File(...), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id, Note.tenant_id == ctx.tenant.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    storage_path, size = store_tenant_file(ctx.tenant.id, file)
    db.add(Attachment(tenant_id=ctx.tenant.id, note_id=note.id, uploaded_by_user_id=ctx.user.id, original_name=file.filename or "upload.bin", storage_path=storage_path, mime_type=file.content_type or "application/octet-stream", size_bytes=size))
    db.commit()
    return RedirectResponse(url=f"/notes?tenant_id={ctx.tenant.id}", status_code=303)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id, Attachment.tenant_id == ctx.tenant.id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path=attachment.storage_path, media_type=attachment.mime_type, filename=attachment.original_name)


@router.post("/tasks")
def create_task(
    title: str = Form(...),
    description: str = Form(""),
    client_id: int | None = Form(None),
    project_id: int | None = Form(None),
    due_date: str | None = Form(None),
    status: str = Form("todo"),
    priority: str = Form("medium"),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    parsed_due = _parse_date(due_date)
    resolved_client_id = client_id
    if client_id:
        client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
        if not client:
            raise HTTPException(status_code=403, detail="Client access denied")
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Project access denied")
        resolved_client_id = project.client_id
    task = Task(
        tenant_id=ctx.tenant.id,
        client_id=resolved_client_id,
        project_id=project_id,
        created_by_user_id=ctx.user.id,
        title=title.strip(),
        description=description.strip(),
        due_date=parsed_due,
        status=status if status in {"todo", "in_progress", "done"} else "todo",
        priority=priority if priority in {"low", "medium", "high"} else "medium",
    )
    db.add(task)
    db.flush()
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="task_created",
        entity_type="task",
        entity_id=task.id,
        severity="info",
        title=f"Task created: {task.title}",
        detail={"detail": f"Due {task.due_date.isoformat()}" if task.due_date else "No due date"},
    )
    db.commit()
    return RedirectResponse(url=f"/tasks?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/tasks/{task_id}/status")
def update_task_status(task_id: int, status: str = Form(...), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.tenant_id == ctx.tenant.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if status not in {"todo", "in_progress", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    task.status = status
    task.completed_at = datetime.utcnow() if status == "done" else None
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="task_status_changed",
        entity_type="task",
        entity_id=task.id,
        severity="info",
        title=f"Task {task.title} moved to {status}",
        detail={"detail": f"Priority {task.priority}"},
    )
    db.commit()
    return RedirectResponse(url=f"/tasks?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/service-jobs")
def create_service_job(title: str = Form(...), service_type: str = Form("general"), scheduled_for: str | None = Form(None), notes: str = Form(""), client_id: int | None = Form(None), project_id: int | None = Form(None), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    parsed_schedule = _parse_date(scheduled_for)
    if client_id:
        client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
        if not client:
            raise HTTPException(status_code=403, detail="Client access denied")
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Project access denied")
    db.add(ServiceJob(tenant_id=ctx.tenant.id, client_id=client_id, project_id=project_id, created_by_user_id=ctx.user.id, title=title.strip(), service_type=service_type.strip() or "general", stage="intake", scheduled_for=parsed_schedule, notes=notes.strip()))
    db.commit()
    return RedirectResponse(url=f"/scheduler?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/service-jobs/{job_id}/stage")
def update_service_job_stage(job_id: int, stage: str = Form(...), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    if stage not in {"intake", "scheduled", "in_service", "completed"}:
        raise HTTPException(status_code=400, detail="Invalid stage")
    job = db.query(ServiceJob).filter(ServiceJob.id == job_id, ServiceJob.tenant_id == ctx.tenant.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Service job not found")
    job.stage = stage
    db.commit()
    return RedirectResponse(url=f"/scheduler?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/calendar-events")
def create_calendar_event(title: str = Form(...), event_date: str = Form(...), notes: str = Form(""), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    parsed_date = _parse_date(event_date)
    if not parsed_date:
        raise HTTPException(status_code=400, detail="event_date required")
    db.add(CalendarEvent(tenant_id=ctx.tenant.id, created_by_user_id=ctx.user.id, title=title.strip(), event_date=parsed_date, notes=notes.strip()))
    db.commit()
    return RedirectResponse(url=f"/calendar?tenant_id={ctx.tenant.id}", status_code=303)
