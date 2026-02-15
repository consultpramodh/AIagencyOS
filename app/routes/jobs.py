import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Job, RunLog, WorkflowRun
from app.services.authz import CurrentContext, require_context

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/stream")
def jobs_stream(
    run_id: int | None = Query(default=None),
    ctx: CurrentContext = Depends(require_context),
    db: Session = Depends(get_db),
):
    def event_generator():
        last_id = 0
        for _ in range(40):
            status = "running"
            progress = 0
            message = "Waiting for job events"

            if run_id:
                run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id, WorkflowRun.tenant_id == ctx.tenant.id).first()
                if run:
                    status = run.status
                logs = (
                    db.query(RunLog)
                    .filter(RunLog.tenant_id == ctx.tenant.id, RunLog.run_id == run_id, RunLog.id > last_id)
                    .order_by(RunLog.id.asc())
                    .all()
                )
                for log in logs:
                    last_id = log.id
                    payload = {
                        "tenant_id": ctx.tenant.id,
                        "status": status,
                        "progress": progress,
                        "message": log.message,
                        "at": log.created_at.isoformat(),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                if run and run.status in {"succeeded", "failed", "blocked", "canceled"}:
                    payload = {
                        "tenant_id": ctx.tenant.id,
                        "status": run.status,
                        "progress": 100 if run.status == "succeeded" else progress,
                        "message": f"Run ended with {run.status}",
                        "at": datetime.utcnow().isoformat(),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    break
            else:
                job = db.query(Job).filter(Job.tenant_id == ctx.tenant.id).order_by(Job.id.desc()).first()
                if job:
                    status = job.status
                    progress = job.progress
                    message = f"Job #{job.id} {job.kind}"
                payload = {
                    "tenant_id": ctx.tenant.id,
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "at": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if status in {"succeeded", "failed", "blocked", "canceled"}:
                    break
            time.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
