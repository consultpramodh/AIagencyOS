import time

from app.main import app
from app.models import Job, WorkflowRun


def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_workflow_run_creates_job_and_reaches_terminal_state(client):
    _login(client, "owner@test.local", "pass1234")

    wf = client.post("/workflows?tenant_id=1", data={"name": "Test Flow", "description": "x"}, follow_redirects=False)
    assert wf.status_code == 303
    location = wf.headers["location"]
    workflow_id = int(location.split("workflow_id=")[1])

    client.post(
        f"/workflows/{workflow_id}/steps?tenant_id=1",
        data={"name": "Auto Step", "action_type": "noop", "agent_key": "ops", "gating_policy": "auto", "config_json": "{}"},
        follow_redirects=False,
    )

    run_resp = client.post(f"/workflows/{workflow_id}/run?tenant_id=1", follow_redirects=False)
    assert run_resp.status_code == 303

    final_status = None
    for _ in range(30):
        db = app.state.testing_sessionmaker()
        try:
            run = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id, WorkflowRun.tenant_id == 1).order_by(WorkflowRun.id.desc()).first()
            job = db.query(Job).filter(Job.tenant_id == 1, Job.kind == "workflow_run").order_by(Job.id.desc()).first()
            if run:
                final_status = run.status
            if run and run.status in {"succeeded", "blocked", "failed", "canceled"} and job and job.status in {"succeeded", "blocked", "failed", "canceled"}:
                break
        finally:
            db.close()
        time.sleep(0.1)

    assert final_status in {"succeeded", "blocked"}
