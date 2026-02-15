from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Attachment, Client, Membership, Note, Project, Task
from app.services.authz import CurrentContext, require_context, require_role
from app.services.storage import store_tenant_file

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    memberships = db.query(Membership).filter(Membership.user_id == ctx.user.id).all()
    clients = db.query(Client).filter(Client.tenant_id == ctx.tenant.id).order_by(Client.id.asc()).all()
    projects = db.query(Project).filter(Project.tenant_id == ctx.tenant.id).order_by(Project.id.asc()).all()
    notes = db.query(Note).filter(Note.tenant_id == ctx.tenant.id).order_by(Note.updated_at.desc()).all()
    tasks = db.query(Task).filter(Task.tenant_id == ctx.tenant.id).order_by(Task.created_at.desc()).all()

    note_ids = [n.id for n in notes]
    attachments = {}
    if note_ids:
        rows = db.query(Attachment).filter(Attachment.tenant_id == ctx.tenant.id, Attachment.note_id.in_(note_ids)).all()
        for item in rows:
            attachments.setdefault(item.note_id, []).append(item)

    today = date.today()
    today_tasks = (
        db.query(Task)
        .filter(
            Task.tenant_id == ctx.tenant.id,
            Task.status != "done",
            Task.due_date.is_not(None),
            Task.due_date <= today,
        )
        .order_by(Task.due_date.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "ctx": ctx,
            "memberships": memberships,
            "clients": clients,
            "projects": projects,
            "notes": notes,
            "tasks_todo": [t for t in tasks if t.status == "todo"],
            "tasks_in_progress": [t for t in tasks if t.status == "in_progress"],
            "tasks_done": [t for t in tasks if t.status == "done"],
            "today_tasks": today_tasks,
            "attachments": attachments,
        },
    )


@router.post("/clients")
def create_client(
    name: str = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = Client(tenant_id=ctx.tenant.id, name=name.strip())
    db.add(client)
    db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/projects")
def create_project(
    client_id: int = Form(...),
    name: str = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if client:
        project = Project(tenant_id=ctx.tenant.id, client_id=client.id, name=name.strip())
        db.add(project)
        db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/notes")
def create_note(
    title: str = Form(...),
    body_markdown: str = Form(""),
    project_id: int | None = Form(None),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Project access denied")

    note = Note(
        tenant_id=ctx.tenant.id,
        project_id=project_id,
        created_by_user_id=ctx.user.id,
        title=title.strip(),
        body_markdown=body_markdown.strip(),
    )
    db.add(note)
    db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}#notes", status_code=303)


@router.post("/notes/{note_id}/update")
def update_note(
    note_id: int,
    title: str = Form(...),
    body_markdown: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    note = db.query(Note).filter(Note.id == note_id, Note.tenant_id == ctx.tenant.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    note.title = title.strip()
    note.body_markdown = body_markdown.strip()
    db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}#notes", status_code=303)


@router.post("/notes/{note_id}/attachments")
def upload_attachment(
    note_id: int,
    file: UploadFile = File(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    note = db.query(Note).filter(Note.id == note_id, Note.tenant_id == ctx.tenant.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    storage_path, size = store_tenant_file(ctx.tenant.id, file)
    attachment = Attachment(
        tenant_id=ctx.tenant.id,
        note_id=note.id,
        uploaded_by_user_id=ctx.user.id,
        original_name=file.filename or "upload.bin",
        storage_path=storage_path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(attachment)
    db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}#notes", status_code=303)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    ctx: CurrentContext = Depends(require_context),
    db: Session = Depends(get_db),
):
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.tenant_id == ctx.tenant.id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return FileResponse(path=attachment.storage_path, media_type=attachment.mime_type, filename=attachment.original_name)


@router.post("/tasks")
def create_task(
    title: str = Form(...),
    description: str = Form(""),
    project_id: int | None = Form(None),
    due_date: str | None = Form(None),
    status: str = Form("todo"),
    priority: str = Form("medium"),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    parsed_due: date | None = None
    if due_date:
        parsed_due = date.fromisoformat(due_date)

    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Project access denied")

    task = Task(
        tenant_id=ctx.tenant.id,
        project_id=project_id,
        created_by_user_id=ctx.user.id,
        title=title.strip(),
        description=description.strip(),
        due_date=parsed_due,
        status=status if status in {"todo", "in_progress", "done"} else "todo",
        priority=priority if priority in {"low", "medium", "high"} else "medium",
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}#tasks", status_code=303)


@router.post("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    status: str = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.tenant_id == ctx.tenant.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if status not in {"todo", "in_progress", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    task.status = status
    db.commit()
    return RedirectResponse(url=f"/?tenant_id={ctx.tenant.id}#tasks", status_code=303)
