from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import ConnectorCredential, ConnectorInstance, ConnectorRun, ConnectorType
from app.services.authz import CurrentContext, require_context, require_role
from app.services.intelligence import audit_change, emit_event

router = APIRouter(prefix="/connectors", tags=["connectors"])
templates = Jinja2Templates(directory="app/templates")

DEFAULT_TYPES = [
    ("google_ads", "Google Ads"),
    ("meta_ads", "Meta Ads"),
    ("ga4", "Google Analytics 4"),
    ("search_console", "Search Console"),
    ("email", "Email Provider"),
    ("books", "Books / Accounting"),
]


@router.get("")
def connector_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    existing = {x.key for x in db.query(ConnectorType).all()}
    for key, name in DEFAULT_TYPES:
        if key not in existing:
            db.add(ConnectorType(key=key, name=name))
    db.commit()

    types = db.query(ConnectorType).order_by(ConnectorType.name.asc()).all()
    instances = db.query(ConnectorInstance).filter(ConnectorInstance.tenant_id == ctx.tenant.id).order_by(ConnectorInstance.id.desc()).all()
    runs = db.query(ConnectorRun).filter(ConnectorRun.tenant_id == ctx.tenant.id).order_by(ConnectorRun.id.desc()).limit(30).all()
    creds = db.query(ConnectorCredential).filter(ConnectorCredential.tenant_id == ctx.tenant.id).all()
    cred_by_instance = {c.connector_instance_id: c for c in creds}

    return templates.TemplateResponse(
        request,
        "connectors.html",
        {"ctx": ctx, "types": types, "instances": instances, "runs": runs, "cred_by_instance": cred_by_instance},
    )


@router.post("")
def create_connector(
    connector_type_id: int = Form(...),
    name: str = Form(...),
    mode: str = Form("manual"),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    ct = db.query(ConnectorType).filter(ConnectorType.id == connector_type_id).first()
    if not ct:
        raise HTTPException(status_code=404, detail="Connector type not found")

    instance = ConnectorInstance(
        tenant_id=ctx.tenant.id,
        connector_type_id=ct.id,
        name=name.strip(),
        mode=mode if mode in {"manual", "api"} else "manual",
        status="active",
        config_json="{}",
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    db.add(
        ConnectorCredential(
            tenant_id=ctx.tenant.id,
            connector_instance_id=instance.id,
            secret_masked="configured-manual" if instance.mode == "manual" else "api-key-missing",
            is_configured=instance.mode == "manual",
        )
    )
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="connector_config_changed",
        entity_type="connector_instance",
        entity_id=instance.id,
        severity="info",
        title=f"Connector configured: {instance.name}",
        detail={"detail": f"Mode {instance.mode}"},
    )
    audit_change(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        entity_type="connector_config",
        entity_id=instance.id,
        action="create",
        before={},
        after={"name": instance.name, "mode": instance.mode, "status": instance.status},
    )
    db.commit()

    return RedirectResponse(url=f"/connectors?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/{instance_id}/run")
def run_connector(
    instance_id: int,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == instance_id, ConnectorInstance.tenant_id == ctx.tenant.id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Connector instance not found")

    run = ConnectorRun(
        tenant_id=ctx.tenant.id,
        connector_instance_id=instance.id,
        status="succeeded",
        log="Manual mode run completed (stub).",
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
    )
    db.add(run)
    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="connector_run_succeeded",
        entity_type="connector_run",
        entity_id=run.id,
        severity="info",
        title=f"Connector run completed: {instance.name}",
        detail={"detail": run.log},
    )
    db.commit()
    return RedirectResponse(url=f"/connectors?tenant_id={ctx.tenant.id}", status_code=303)
