from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Activity, Client, Contact, Deal, DealStage, Project
from app.services.authz import CurrentContext, require_context, require_role
from app.services.intelligence import audit_change, emit_event

router = APIRouter(prefix="/crm", tags=["crm"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def crm_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    stages = db.query(DealStage).filter(DealStage.tenant_id == ctx.tenant.id).order_by(DealStage.position.asc()).all()
    if not stages:
        for i, name in enumerate(["Lead", "Qualified", "Proposal", "Won"], start=1):
            db.add(DealStage(tenant_id=ctx.tenant.id, name=name, position=i, is_won=name == "Won"))
        db.commit()
        stages = db.query(DealStage).filter(DealStage.tenant_id == ctx.tenant.id).order_by(DealStage.position.asc()).all()

    clients = db.query(Client).filter(Client.tenant_id == ctx.tenant.id).order_by(Client.name.asc()).all()
    contacts = db.query(Contact).filter(Contact.tenant_id == ctx.tenant.id).order_by(Contact.name.asc()).all()
    deals = db.query(Deal).filter(Deal.tenant_id == ctx.tenant.id).order_by(Deal.id.desc()).all()
    projects = db.query(Project).filter(Project.tenant_id == ctx.tenant.id).order_by(Project.name.asc()).all()
    activities = db.query(Activity).filter(Activity.tenant_id == ctx.tenant.id).order_by(Activity.id.desc()).limit(20).all()

    deals_by_stage = {stage.id: [] for stage in stages}
    for deal in deals:
        deals_by_stage.setdefault(deal.stage_id, []).append(deal)

    return templates.TemplateResponse(
        request,
        "crm.html",
        {
            "ctx": ctx,
            "stages": stages,
            "clients": clients,
            "contacts": contacts,
            "deals_by_stage": deals_by_stage,
            "projects": projects,
            "activities": activities,
        },
    )


@router.post("/contacts")
def create_contact(
    client_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    role_title: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if not client:
        raise HTTPException(status_code=403, detail="Client access denied")

    db.add(
        Contact(
            tenant_id=ctx.tenant.id,
            client_id=client_id,
            name=name.strip(),
            email=email.strip(),
            phone=phone.strip(),
            role_title=role_title.strip(),
        )
    )
    db.commit()
    return RedirectResponse(url=f"/crm?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/deals")
def create_deal(
    client_id: int = Form(...),
    title: str = Form(...),
    value_cents: int = Form(0),
    stage_id: int = Form(...),
    contact_id: int | None = Form(None),
    close_date: str | None = Form(None),
    probability_pct: int = Form(0),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    stage = db.query(DealStage).filter(DealStage.id == stage_id, DealStage.tenant_id == ctx.tenant.id).first()
    if not client or not stage:
        raise HTTPException(status_code=403, detail="Invalid deal references")

    if contact_id:
        contact = db.query(Contact).filter(Contact.id == contact_id, Contact.tenant_id == ctx.tenant.id).first()
        if not contact:
            raise HTTPException(status_code=403, detail="Contact access denied")

    parsed_close = None
    if close_date:
        from datetime import date

        parsed_close = date.fromisoformat(close_date)

    deal = Deal(
        tenant_id=ctx.tenant.id,
        client_id=client_id,
        contact_id=contact_id,
        stage_id=stage_id,
        title=title.strip(),
        value_cents=value_cents,
        close_date=parsed_close,
        probability_pct=max(0, min(100, probability_pct)),
        status="open",
    )
    db.add(deal)
    db.flush()
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="deal_created",
        entity_type="deal",
        entity_id=deal.id,
        severity="info",
        title=f"Deal created: {deal.title}",
        detail={"detail": f"${deal.value_cents / 100:.2f} in stage {stage.name}"},
    )
    db.commit()
    return RedirectResponse(url=f"/crm?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/deals/{deal_id}/stage")
def move_deal_stage(
    deal_id: int,
    stage_id: int = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.tenant_id == ctx.tenant.id).first()
    stage = db.query(DealStage).filter(DealStage.id == stage_id, DealStage.tenant_id == ctx.tenant.id).first()
    if not deal or not stage:
        raise HTTPException(status_code=404, detail="Deal not found")
    old_stage_id = deal.stage_id
    deal.stage_id = stage_id
    deal.status = "won" if stage.is_won else "open"
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="deal_stage_changed",
        entity_type="deal",
        entity_id=deal.id,
        severity="info",
        title=f"Deal stage changed: {deal.title}",
        detail={"detail": f"Stage {old_stage_id} -> {stage_id}"},
    )
    audit_change(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        entity_type="deal",
        entity_id=deal.id,
        action="stage_changed",
        before={"stage_id": old_stage_id},
        after={"stage_id": stage_id, "status": deal.status},
    )
    db.commit()
    return RedirectResponse(url=f"/crm?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/deals/{deal_id}/link-project")
def link_deal_project(
    deal_id: int,
    project_id: int = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.tenant_id == ctx.tenant.id).first()
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
    if not deal or not project:
        raise HTTPException(status_code=404, detail="Deal or project not found")
    deal.project_id = project.id
    db.commit()
    return RedirectResponse(url=f"/crm?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/activities")
def create_activity(
    client_id: int = Form(...),
    deal_id: int | None = Form(None),
    activity_type: str = Form("task"),
    summary: str = Form(...),
    due_date: str | None = Form(None),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    parsed_due = None
    if due_date:
        from datetime import date

        parsed_due = date.fromisoformat(due_date)

    if deal_id:
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.tenant_id == ctx.tenant.id).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

    db.add(
        Activity(
            tenant_id=ctx.tenant.id,
            client_id=client_id,
            deal_id=deal_id,
            activity_type=activity_type,
            summary=summary.strip(),
            due_date=parsed_due,
            status="open",
        )
    )
    db.commit()
    return RedirectResponse(url=f"/crm?tenant_id={ctx.tenant.id}", status_code=303)
