from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import ApprovalRequest, Note, Task, WorkflowRun
from app.services.authz import CurrentContext, require_context

router = APIRouter(prefix="/m", tags=["mobile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def mobile_home(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    today = date.today()
    today_tasks = (
        db.query(Task)
        .filter(Task.tenant_id == ctx.tenant.id, Task.status != "done", Task.due_date.is_not(None), Task.due_date <= today)
        .order_by(Task.due_date.asc())
        .limit(12)
        .all()
    )
    approvals = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.tenant_id == ctx.tenant.id, ApprovalRequest.status == "pending")
        .order_by(ApprovalRequest.requested_at.asc())
        .limit(12)
        .all()
    )
    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.tenant_id == ctx.tenant.id)
        .order_by(WorkflowRun.id.desc())
        .limit(12)
        .all()
    )
    notes = db.query(Note).filter(Note.tenant_id == ctx.tenant.id).order_by(Note.updated_at.desc()).limit(8).all()

    return templates.TemplateResponse(
        request,
        "mobile.html",
        {"ctx": ctx, "today_tasks": today_tasks, "approvals": approvals, "runs": runs, "notes": notes},
    )
