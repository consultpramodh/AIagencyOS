from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.authz import CurrentContext, require_context
from app.models import AuditLog
from app.services.intelligence import weekly_snapshot, write_weekly_artifacts

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/weekly")
def weekly_report(
    request: Request,
    export: str | None = Query(default=None),
    fmt: str = Query(default="html"),
    ctx: CurrentContext = Depends(require_context),
    db: Session = Depends(get_db),
):
    snapshot = weekly_snapshot(db, ctx.tenant.id, date.today())
    html_path, csv_path = write_weekly_artifacts(ctx.tenant.id, snapshot)

    if export == "1":
        if fmt == "csv":
            return FileResponse(path=str(csv_path), media_type="text/csv", filename=csv_path.name)
        return FileResponse(path=str(html_path), media_type="text/html", filename=html_path.name)

    return templates.TemplateResponse(
        request,
        "reports_weekly.html",
        {
            "ctx": ctx,
            "snapshot": snapshot,
            "artifact_html": str(html_path),
            "artifact_csv": str(csv_path),
        },
    )


@router.get("/audit")
def audit_page(
    request: Request,
    ctx: CurrentContext = Depends(require_context),
    db: Session = Depends(get_db),
):
    rows = db.query(AuditLog).filter(AuditLog.tenant_id == ctx.tenant.id).order_by(AuditLog.id.desc()).limit(200).all()
    return templates.TemplateResponse(request, "audit.html", {"ctx": ctx, "rows": rows})
