import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import ApprovalRequest, Job, RunLog, WorkflowRun, WorkflowStep, WorkflowTemplate
from app.services.authz import CurrentContext, require_context, require_role
from app.services.workflow_engine import approve_run, enqueue_workflow_run

router = APIRouter(prefix="/workflows", tags=["workflows"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def workflow_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    workflows = db.query(WorkflowTemplate).filter(WorkflowTemplate.tenant_id == ctx.tenant.id).order_by(WorkflowTemplate.id.desc()).all()
    selected_id = request.query_params.get("workflow_id")
    selected = workflows[0] if workflows else None
    if selected_id:
        selected = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == int(selected_id), WorkflowTemplate.tenant_id == ctx.tenant.id).first() or selected

    steps = []
    runs = []
    logs = []
    approvals = []
    if selected:
        steps = db.query(WorkflowStep).filter(WorkflowStep.workflow_id == selected.id, WorkflowStep.tenant_id == ctx.tenant.id).order_by(WorkflowStep.step_order.asc()).all()
        runs = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == selected.id, WorkflowRun.tenant_id == ctx.tenant.id).order_by(WorkflowRun.id.desc()).limit(20).all()
        if runs:
            logs = db.query(RunLog).filter(RunLog.run_id == runs[0].id, RunLog.tenant_id == ctx.tenant.id).order_by(RunLog.id.desc()).limit(40).all()
            approvals = db.query(ApprovalRequest).filter(ApprovalRequest.run_id == runs[0].id, ApprovalRequest.tenant_id == ctx.tenant.id).order_by(ApprovalRequest.id.desc()).all()

    jobs = db.query(Job).filter(Job.tenant_id == ctx.tenant.id).order_by(Job.id.desc()).limit(20).all()

    return templates.TemplateResponse(
        request,
        "workflows.html",
        {
            "ctx": ctx,
            "workflows": workflows,
            "selected": selected,
            "steps": steps,
            "runs": runs,
            "logs": logs,
            "jobs": jobs,
            "approvals": approvals,
        },
    )


@router.post("")
def create_workflow(
    name: str = Form(...),
    description: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    workflow = WorkflowTemplate(
        tenant_id=ctx.tenant.id,
        name=name.strip(),
        description=description.strip(),
        version=1,
        created_by_user_id=ctx.user.id,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return RedirectResponse(url=f"/workflows?tenant_id={ctx.tenant.id}&workflow_id={workflow.id}", status_code=303)


@router.post("/{workflow_id}/steps")
def create_step(
    workflow_id: int,
    name: str = Form(...),
    action_type: str = Form("manual"),
    agent_key: str = Form("ops_lead"),
    gating_policy: str = Form("approve"),
    config_json: str = Form("{}"),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    workflow = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == workflow_id, WorkflowTemplate.tenant_id == ctx.tenant.id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        json.loads(config_json)
    except Exception:
        config_json = "{}"

    order = db.query(WorkflowStep).filter(WorkflowStep.workflow_id == workflow_id, WorkflowStep.tenant_id == ctx.tenant.id).count() + 1
    db.add(
        WorkflowStep(
            tenant_id=ctx.tenant.id,
            workflow_id=workflow_id,
            step_order=order,
            name=name.strip(),
            action_type=action_type.strip(),
            agent_key=agent_key.strip(),
            config_json=config_json,
            gating_policy=gating_policy if gating_policy in {"approve", "auto", "pause"} else "approve",
        )
    )
    db.commit()
    return RedirectResponse(url=f"/workflows?tenant_id={ctx.tenant.id}&workflow_id={workflow_id}", status_code=303)


@router.post("/{workflow_id}/run")
def run_workflow(
    workflow_id: int,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    workflow = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == workflow_id, WorkflowTemplate.tenant_id == ctx.tenant.id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    run = WorkflowRun(tenant_id=ctx.tenant.id, workflow_id=workflow.id, status="queued", triggered_by_user_id=ctx.user.id)
    db.add(run)
    db.commit()
    db.refresh(run)

    enqueue_workflow_run(ctx.tenant.id, run.id)
    return RedirectResponse(url=f"/workflows?tenant_id={ctx.tenant.id}&workflow_id={workflow_id}", status_code=303)


@router.post("/runs/{run_id}/approve")
def approve_workflow_run(
    run_id: int,
    ctx: CurrentContext = Depends(require_role("admin")),
):
    approve_run(run_id=run_id, tenant_id=ctx.tenant.id, user_id=ctx.user.id)
    return RedirectResponse(url=f"/workflows?tenant_id={ctx.tenant.id}", status_code=303)
