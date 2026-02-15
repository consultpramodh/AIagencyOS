from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import (
    ApprovalRequest,
    Attachment,
    CalendarEvent,
    Client,
    Job,
    Membership,
    Note,
    Project,
    ServiceJob,
    Task,
    WorkflowRun,
)
from app.services.authz import CurrentContext, require_context, require_role
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
    rows.sort(key=lambda x: x[0])
    return rows


@router.get("/")
def home(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    today_tasks = _today_tasks(ctx, db)
    approvals_pending = db.query(ApprovalRequest).filter(ApprovalRequest.tenant_id == ctx.tenant.id, ApprovalRequest.status == "pending").count()
    recent_jobs = db.query(Job).filter(Job.tenant_id == ctx.tenant.id).order_by(Job.id.desc()).limit(6).all()
    recent_runs = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == ctx.tenant.id).order_by(WorkflowRun.id.desc()).limit(6).all()
    pulse_metrics = [
        {"label": "Approvals", "value": approvals_pending, "trend": "pending", "direction": "down" if approvals_pending else "flat"},
        {"label": "Due Tasks", "value": len(today_tasks), "trend": "today", "direction": "down" if today_tasks else "flat"},
        {"label": "Active Jobs", "value": len(recent_jobs), "trend": "live", "direction": "up" if recent_jobs else "flat"},
    ]
    intelligence_items = []
    for task in today_tasks[:4]:
        intelligence_items.append(
            {
                "title": f"Task due: {task.title}",
                "meta": f"Due {task.due_date}" if task.due_date else "No due date",
                "detail": "Prioritize this in today's execution queue.",
                "level": "risk",
            }
        )
    for run in recent_runs[:4]:
        intelligence_items.append(
            {
                "title": f"Workflow run #{run.id} is {run.status}",
                "meta": "Automation telemetry",
                "detail": "Open workflow detail to inspect step logs and approvals.",
                "level": "neutral" if run.status in {"queued", "running"} else ("good" if run.status == "succeeded" else "risk"),
            }
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            **base,
            "today_tasks": today_tasks,
            "calendar_rows": _calendar_rows(ctx, db)[:8],
            "approvals_pending": approvals_pending,
            "recent_jobs": recent_jobs,
            "recent_runs": recent_runs,
            "pulse_metrics": pulse_metrics,
            "intelligence_items": intelligence_items,
        },
    )


@router.get("/operations")
def operations_hub(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    return templates.TemplateResponse(request, "operations.html", {**base, "today_tasks": _today_tasks(ctx, db)})


@router.get("/clients")
def clients_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    return templates.TemplateResponse(request, "clients.html", base)


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
    return templates.TemplateResponse(request, "calendar.html", {**base, "calendar_rows": _calendar_rows(ctx, db)})


@router.post("/clients")
def create_client(
    name: str = Form(...),
    contact_name: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    db.add(Client(tenant_id=ctx.tenant.id, name=name.strip(), contact_name=contact_name.strip(), contact_email=contact_email.strip(), contact_phone=contact_phone.strip()))
    db.commit()
    return RedirectResponse(url=f"/clients?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/projects")
def create_project(client_id: int = Form(...), name: str = Form(...), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if client:
        db.add(Project(tenant_id=ctx.tenant.id, client_id=client.id, name=name.strip()))
        db.commit()
    return RedirectResponse(url=f"/projects?tenant_id={ctx.tenant.id}", status_code=303)


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
def create_task(title: str = Form(...), description: str = Form(""), project_id: int | None = Form(None), due_date: str | None = Form(None), status: str = Form("todo"), priority: str = Form("medium"), ctx: CurrentContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    parsed_due = _parse_date(due_date)
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Project access denied")
    db.add(Task(tenant_id=ctx.tenant.id, project_id=project_id, created_by_user_id=ctx.user.id, title=title.strip(), description=description.strip(), due_date=parsed_due, status=status if status in {"todo", "in_progress", "done"} else "todo", priority=priority if priority in {"low", "medium", "high"} else "medium"))
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
