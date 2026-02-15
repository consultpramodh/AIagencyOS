import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    Approval,
    ApprovalRequest,
    AuditLog,
    Client,
    ClientFinancial,
    Deal,
    Event,
    Job,
    Task,
    WorkflowRun,
)


def emit_event(
    db: Session,
    *,
    tenant_id: int,
    event_type: str,
    entity_type: str,
    entity_id: int,
    severity: str,
    title: str,
    detail: dict | None = None,
) -> Event:
    row = Event(
        tenant_id=tenant_id,
        type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        title=title,
        detail_json=json.dumps(detail or {}),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def audit_change(
    db: Session,
    *,
    tenant_id: int,
    actor_user_id: int | None,
    entity_type: str,
    entity_id: int,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    row = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=json.dumps(before or {}),
        after_json=json.dumps(after or {}),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


@dataclass
class HealthScore:
    client_id: int
    score: int
    risk_level: str
    drivers: list[str]
    opportunities: list[str]


def compute_client_health(db: Session, tenant_id: int, client_id: int) -> HealthScore:
    today = date.today()
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    overdue_tasks = (
        db.query(Task)
        .filter(Task.tenant_id == tenant_id, Task.client_id == client_id, Task.status != "done", Task.due_date.is_not(None), Task.due_date < today)
        .count()
    )
    pending_approvals = db.query(Approval).filter(Approval.tenant_id == tenant_id, Approval.client_id == client_id, Approval.status == "pending").count()
    blocked_runs = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == tenant_id, WorkflowRun.client_id == client_id, WorkflowRun.status == "blocked").count()
    recent_failures = (
        db.query(Event)
        .filter(Event.tenant_id == tenant_id, Event.entity_type == "workflow_run", Event.type == "workflow_run_failed", Event.created_at >= week_ago)
        .count()
    )

    fin = db.query(ClientFinancial).filter(ClientFinancial.tenant_id == tenant_id, ClientFinancial.client_id == client_id).first()
    renewal_due_bucket = 0
    drivers: list[str] = []
    if fin and fin.renewal_date:
        days = (fin.renewal_date - today).days
        if days <= 14:
            renewal_due_bucket = 20
            drivers.append(f"Renewal due in {days} days")

    pipeline_14d = (
        db.query(Deal)
        .filter(Deal.tenant_id == tenant_id, Deal.client_id == client_id, Deal.close_date.is_not(None), Deal.close_date <= today + timedelta(days=14))
        .all()
    )
    pipeline_14d_value = sum(x.value_cents for x in pipeline_14d)

    last_activity = (
        db.query(Activity)
        .filter(Activity.tenant_id == tenant_id, Activity.client_id == client_id)
        .order_by(Activity.created_at.desc())
        .first()
    )
    inactivity_days = 0
    if last_activity:
        inactivity_days = (datetime.utcnow().date() - last_activity.created_at.date()).days
    else:
        inactivity_days = 30

    success_runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.tenant_id == tenant_id, WorkflowRun.client_id == client_id, WorkflowRun.status == "succeeded", WorkflowRun.created_at >= month_ago)
        .count()
    )

    risk_score = min(
        100,
        int(overdue_tasks * 8 + pending_approvals * 12 + blocked_runs * 20 + recent_failures * 15 + inactivity_days * 1.2 + renewal_due_bucket),
    )
    opp_score = min(100, int((pipeline_14d_value / 100000) * 12 + success_runs * 2))
    final_score = max(0, min(100, risk_score - int(opp_score * 0.35)))

    if blocked_runs:
        drivers.append(f"{blocked_runs} blocked workflow runs")
    if overdue_tasks:
        drivers.append(f"{overdue_tasks} overdue tasks")
    if pending_approvals:
        drivers.append(f"{pending_approvals} pending approvals")
    if recent_failures:
        drivers.append(f"{recent_failures} recent failures")
    if inactivity_days >= 7:
        drivers.append(f"No activity in {inactivity_days} days")

    opp_drivers: list[str] = []
    if pipeline_14d_value:
        opp_drivers.append(f"${pipeline_14d_value / 100:.2f} pipeline closing <14d")
    if success_runs:
        opp_drivers.append(f"{success_runs} successful workflow runs in last 30d")

    risk_level = "Low"
    if final_score >= 70:
        risk_level = "High"
    elif final_score >= 40:
        risk_level = "Med"

    return HealthScore(client_id=client_id, score=final_score, risk_level=risk_level, drivers=drivers[:4], opportunities=opp_drivers[:3])


def weekly_snapshot(db: Session, tenant_id: int, report_date: date) -> dict:
    week_start = report_date - timedelta(days=7)
    mrr_total = sum(x.mrr_cents for x in db.query(ClientFinancial).filter(ClientFinancial.tenant_id == tenant_id).all())
    pipeline_14d = (
        db.query(Deal)
        .filter(Deal.tenant_id == tenant_id, Deal.close_date.is_not(None), Deal.close_date <= report_date + timedelta(days=14))
        .all()
    )
    pipeline_value = sum(x.value_cents for x in pipeline_14d)
    blocked_items = db.query(Approval).filter(Approval.tenant_id == tenant_id, Approval.status == "pending").count()
    wins = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.tenant_id == tenant_id, WorkflowRun.status == "succeeded", WorkflowRun.created_at >= datetime.combine(week_start, datetime.min.time()))
        .count()
    )
    recent_events = db.query(Event).filter(Event.tenant_id == tenant_id).order_by(Event.created_at.desc()).limit(20).all()
    top_risks = [x.title for x in recent_events if x.severity in {"high", "critical"}][:5]

    return {
        "report_date": report_date.isoformat(),
        "mrr_total_cents": mrr_total,
        "pipeline_14d_cents": pipeline_value,
        "blocked_items": blocked_items,
        "wins": wins,
        "top_risks": top_risks,
    }


def write_weekly_artifacts(tenant_id: int, snapshot: dict) -> tuple[Path, Path]:
    out_dir = Path("data") / "reports" / f"tenant_{tenant_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = snapshot["report_date"]
    html_path = out_dir / f"{stamp}.html"
    csv_path = out_dir / f"{stamp}.csv"

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Weekly Snapshot {stamp}</title></head>
<body>
  <h1>Weekly Command Snapshot ({stamp})</h1>
  <ul>
    <li>MRR Total: ${snapshot['mrr_total_cents']/100:.2f}</li>
    <li>Pipeline &lt;14d: ${snapshot['pipeline_14d_cents']/100:.2f}</li>
    <li>Blocked approvals: {snapshot['blocked_items']}</li>
    <li>Workflow wins: {snapshot['wins']}</li>
  </ul>
  <h2>Top Risks</h2>
  <ul>{"".join(f"<li>{x}</li>" for x in snapshot["top_risks"])}</ul>
</body></html>
""".strip()
    html_path.write_text(html, encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["report_date", snapshot["report_date"]])
        writer.writerow(["mrr_total_cents", snapshot["mrr_total_cents"]])
        writer.writerow(["pipeline_14d_cents", snapshot["pipeline_14d_cents"]])
        writer.writerow(["blocked_items", snapshot["blocked_items"]])
        writer.writerow(["wins", snapshot["wins"]])
    return html_path, csv_path

