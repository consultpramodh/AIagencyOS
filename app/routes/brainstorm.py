import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import AIOutput, BrainstormQA, BrainstormSession, Recommendation, WorkflowStep, WorkflowTemplate
from app.services.authz import CurrentContext, require_context, require_role
from app.services.brainstorm import build_recommendation, default_questions

router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def brainstorm_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    sessions = db.query(BrainstormSession).filter(BrainstormSession.tenant_id == ctx.tenant.id).order_by(BrainstormSession.id.desc()).all()
    selected = sessions[0] if sessions else None
    selected_id = request.query_params.get("session_id")
    if selected_id:
        selected = db.query(BrainstormSession).filter(BrainstormSession.id == int(selected_id), BrainstormSession.tenant_id == ctx.tenant.id).first() or selected

    qas = []
    rec = None
    if selected:
        qas = db.query(BrainstormQA).filter(BrainstormQA.session_id == selected.id, BrainstormQA.tenant_id == ctx.tenant.id).order_by(BrainstormQA.question_order.asc()).all()
        rec = db.query(Recommendation).filter(Recommendation.session_id == selected.id, Recommendation.tenant_id == ctx.tenant.id).order_by(Recommendation.id.desc()).first()

    return templates.TemplateResponse(
        request,
        "brainstorm.html",
        {"ctx": ctx, "sessions": sessions, "selected": selected, "qas": qas, "rec": rec},
    )


@router.post("")
def create_session(
    title: str = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    session = BrainstormSession(tenant_id=ctx.tenant.id, title=title.strip(), created_by_user_id=ctx.user.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    for idx, q in enumerate(default_questions(), start=1):
        db.add(BrainstormQA(tenant_id=ctx.tenant.id, session_id=session.id, question_order=idx, question=q, answer=""))
    db.commit()

    return RedirectResponse(url=f"/brainstorm?tenant_id={ctx.tenant.id}&session_id={session.id}", status_code=303)


@router.post("/{session_id}/answers/{qa_id}")
def save_single_answer(
    session_id: int,
    qa_id: int,
    answer: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    qa = db.query(BrainstormQA).filter(BrainstormQA.id == qa_id, BrainstormQA.session_id == session_id, BrainstormQA.tenant_id == ctx.tenant.id).first()
    if not qa:
        raise HTTPException(status_code=404, detail="Question not found")
    qa.answer = answer.strip()
    db.commit()
    return RedirectResponse(url=f"/brainstorm?tenant_id={ctx.tenant.id}&session_id={session_id}", status_code=303)


@router.post("/{session_id}/recommend")
def generate_recommendation(
    session_id: int,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    session = db.query(BrainstormSession).filter(BrainstormSession.id == session_id, BrainstormSession.tenant_id == ctx.tenant.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    qas = db.query(BrainstormQA).filter(BrainstormQA.session_id == session.id, BrainstormQA.tenant_id == ctx.tenant.id).order_by(BrainstormQA.question_order.asc()).all()
    rec_data = build_recommendation(session.title, [x.answer for x in qas])

    rec = Recommendation(
        tenant_id=ctx.tenant.id,
        session_id=session.id,
        agent_org_json=json.dumps(rec_data["agent_org"]),
        workflow_draft_json=json.dumps(rec_data["workflow_steps"]),
        metrics_json=json.dumps(rec_data["metrics"]),
    )
    db.add(rec)
    db.add(
        AIOutput(
            tenant_id=ctx.tenant.id,
            session_id=session.id,
            prompt_version="heuristic-v1",
            model="heuristic",
            input_summary=rec_data["summary"],
            output_text=json.dumps(rec_data),
        )
    )
    db.commit()
    return RedirectResponse(url=f"/brainstorm?tenant_id={ctx.tenant.id}&session_id={session.id}", status_code=303)


@router.post("/{session_id}/create-workflow")
def create_workflow_from_recommendation(
    session_id: int,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rec = db.query(Recommendation).filter(Recommendation.session_id == session_id, Recommendation.tenant_id == ctx.tenant.id).order_by(Recommendation.id.desc()).first()
    session = db.query(BrainstormSession).filter(BrainstormSession.id == session_id, BrainstormSession.tenant_id == ctx.tenant.id).first()
    if not rec or not session:
        raise HTTPException(status_code=404, detail="Recommendation missing")

    workflow = WorkflowTemplate(
        tenant_id=ctx.tenant.id,
        name=f"Brainstorm: {session.title}",
        description="Generated from brainstorm",
        version=1,
        created_by_user_id=ctx.user.id,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    steps = json.loads(rec.workflow_draft_json or "[]")
    for idx, step in enumerate(steps, start=1):
        db.add(
            WorkflowStep(
                tenant_id=ctx.tenant.id,
                workflow_id=workflow.id,
                step_order=idx,
                name=step.get("name", f"Step {idx}"),
                action_type=step.get("action_type", "manual"),
                agent_key=step.get("agent_key", "ops_lead"),
                gating_policy=step.get("gating_policy", "approve"),
                config_json="{}",
            )
        )
    db.commit()

    return RedirectResponse(url=f"/workflows?tenant_id={ctx.tenant.id}&workflow_id={workflow.id}", status_code=303)
