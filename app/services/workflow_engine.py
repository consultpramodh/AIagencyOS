import json
import time
from datetime import datetime

import app.core.db as core_db
from app.models import Approval, ApprovalRequest, Job, RunLog, RunStep, WorkflowRun, WorkflowStep
from app.services.intelligence import audit_change, emit_event


TERMINAL = {"succeeded", "failed", "blocked", "canceled"}


def enqueue_workflow_run(tenant_id: int, run_id: int) -> Job:
    db = core_db.SessionLocal()
    try:
        job = Job(tenant_id=tenant_id, kind="workflow_run", status="queued", progress=0, payload_json=json.dumps({"run_id": run_id}))
        db.add(job)
        db.commit()
        db.refresh(job)
    finally:
        db.close()

    # Execute inline to keep DB session behavior deterministic across local sqlite
    # and tests; UI still receives progress updates via job/run state polling/SSE.
    _execute_workflow_job(job.id)
    return job


def _log(db, tenant_id: int, run_id: int, msg: str, level: str = "info"):
    db.add(RunLog(tenant_id=tenant_id, run_id=run_id, level=level, message=msg))


def _execute_workflow_job(job_id: int) -> None:
    db = core_db.SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        payload = json.loads(job.payload_json or "{}")
        run_id = int(payload.get("run_id"))

        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id, WorkflowRun.tenant_id == job.tenant_id).first()
        if not run:
            job.status = "failed"
            job.error_message = "Run not found"
            db.commit()
            return

        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == run.workflow_id, WorkflowStep.tenant_id == run.tenant_id)
            .order_by(WorkflowStep.step_order.asc())
            .all()
        )
        total = max(1, len(steps))

        run.status = "running"
        run.started_at = datetime.utcnow()
        job.status = "running"
        _log(db, run.tenant_id, run.id, "Workflow started")
        db.commit()

        for idx, step in enumerate(steps, start=1):
            rs = RunStep(
                tenant_id=run.tenant_id,
                run_id=run.id,
                step_name=step.name,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(rs)
            _log(db, run.tenant_id, run.id, f"Step {idx}: {step.name} started")
            db.commit()

            if step.gating_policy == "approve":
                rs.status = "blocked"
                rs.ended_at = datetime.utcnow()
                run.status = "blocked"
                job.status = "blocked"
                job.progress = int((idx - 1) / total * 100)
                db.add(
                    ApprovalRequest(
                        tenant_id=run.tenant_id,
                        run_id=run.id,
                        step_name=step.name,
                        status="pending",
                    )
                )
                db.add(
                    Approval(
                        tenant_id=run.tenant_id,
                        client_id=run.client_id,
                        project_id=run.project_id,
                        workflow_run_id=run.id,
                        status="pending",
                        title=f"{step.name} approval",
                        requested_by_user_id=run.triggered_by_user_id,
                    )
                )
                emit_event(
                    db,
                    tenant_id=run.tenant_id,
                    event_type="workflow_run_blocked",
                    entity_type="workflow_run",
                    entity_id=run.id,
                    severity="high",
                    title=f"Blocked workflow requires approval (Run #{run.id})",
                    detail={"detail": f"Step {step.name} is blocked for approval"},
                )
                _log(db, run.tenant_id, run.id, f"Step {idx} blocked for approval")
                db.commit()
                return

            time.sleep(0.2)
            rs.status = "succeeded"
            rs.output_json = json.dumps({"action_type": step.action_type, "agent_key": step.agent_key})
            rs.ended_at = datetime.utcnow()
            job.progress = int(idx / total * 100)
            _log(db, run.tenant_id, run.id, f"Step {idx}: {step.name} completed")
            db.commit()

        run.status = "succeeded"
        run.ended_at = datetime.utcnow()
        job.status = "succeeded"
        job.progress = 100
        _log(db, run.tenant_id, run.id, "Workflow succeeded")
        emit_event(
            db,
            tenant_id=run.tenant_id,
            event_type="workflow_run_succeeded",
            entity_type="workflow_run",
            entity_id=run.id,
            severity="info",
            title=f"Workflow run succeeded (Run #{run.id})",
            detail={"detail": "Execution completed"},
        )
        db.commit()
    except Exception as exc:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            run = db.query(WorkflowRun).filter(WorkflowRun.id == json.loads(job.payload_json or "{}").get("run_id")).first()
            if run:
                emit_event(
                    db,
                    tenant_id=run.tenant_id,
                    event_type="workflow_run_failed",
                    entity_type="workflow_run",
                    entity_id=run.id,
                    severity="high",
                    title=f"Workflow run failed (Run #{run.id})",
                    detail={"detail": str(exc)},
                )
            db.commit()
    finally:
        db.close()


def approve_run(run_id: int, tenant_id: int, user_id: int) -> None:
    db = core_db.SessionLocal()
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id, WorkflowRun.tenant_id == tenant_id).first()
        if not run or run.status != "blocked":
            return

        approval = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.run_id == run_id, ApprovalRequest.tenant_id == tenant_id, ApprovalRequest.status == "pending")
            .order_by(ApprovalRequest.id.asc())
            .first()
        )
        if approval:
            before_status = approval.status
            approval.status = "approved"
            approval.decided_at = datetime.utcnow()
            approval.decided_by_user_id = user_id
            mirror = (
                db.query(Approval)
                .filter(Approval.workflow_run_id == run_id, Approval.tenant_id == tenant_id, Approval.status == "pending")
                .order_by(Approval.id.asc())
                .first()
            )
            if mirror:
                mirror.status = "approved"
                mirror.decided_at = datetime.utcnow()
            emit_event(
                db,
                tenant_id=tenant_id,
                event_type="approval_pending",
                entity_type="approval",
                entity_id=approval.id,
                severity="info",
                title=f"Approval resolved for run #{run_id}",
                detail={"detail": f"Status {before_status} -> approved"},
            )
            audit_change(
                db,
                tenant_id=tenant_id,
                actor_user_id=user_id,
                entity_type="approval",
                entity_id=approval.id,
                action="approved",
                before={"status": before_status},
                after={"status": "approved"},
            )

        run.status = "running"

        blocked_step = (
            db.query(RunStep)
            .filter(RunStep.run_id == run_id, RunStep.tenant_id == tenant_id, RunStep.status == "blocked")
            .order_by(RunStep.id.desc())
            .first()
        )
        if blocked_step:
            blocked_step.status = "succeeded"
            blocked_step.ended_at = datetime.utcnow()

        _log(db, tenant_id, run_id, "Approval granted, workflow resumed")

        steps = db.query(WorkflowStep).filter(WorkflowStep.workflow_id == run.workflow_id, WorkflowStep.tenant_id == tenant_id).order_by(WorkflowStep.step_order.asc()).all()
        finished_names = {x.step_name for x in db.query(RunStep).filter(RunStep.run_id == run_id, RunStep.tenant_id == tenant_id, RunStep.status == "succeeded").all()}
        remaining = [s for s in steps if s.name not in finished_names]

        for idx, step in enumerate(remaining, start=1):
            rs = RunStep(tenant_id=tenant_id, run_id=run_id, step_name=step.name, status="running", started_at=datetime.utcnow())
            db.add(rs)
            _log(db, tenant_id, run_id, f"Resumed step: {step.name}")
            db.commit()
            time.sleep(0.15)
            rs.status = "succeeded"
            rs.ended_at = datetime.utcnow()
            db.commit()

        run.status = "succeeded"
        run.ended_at = datetime.utcnow()
        job = db.query(Job).filter(Job.tenant_id == tenant_id, Job.kind == "workflow_run").order_by(Job.id.desc()).first()
        if job and job.status in {"blocked", "running", "queued"}:
            job.status = "succeeded"
            job.progress = 100
        _log(db, tenant_id, run_id, "Workflow succeeded")
        db.commit()
    finally:
        db.close()
