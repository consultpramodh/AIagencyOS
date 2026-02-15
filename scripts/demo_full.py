import os
import sys
import time
from datetime import date

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


def main() -> None:
    client = TestClient(app)

    login = client.post("/login", data={"email": "owner@demo.local", "password": "demo1234"}, follow_redirects=False)
    print("login:", login.status_code)

    crm = client.get("/crm?tenant_id=1")
    print("crm page:", crm.status_code)

    wf = client.post("/workflows?tenant_id=1", data={"name": "Demo Full Workflow", "description": "full demo"}, follow_redirects=False)
    print("workflow create:", wf.status_code)
    workflow_id = int(wf.headers["location"].split("workflow_id=")[1])

    client.post(f"/workflows/{workflow_id}/steps?tenant_id=1", data={"name": "Auto Step", "action_type": "noop", "agent_key": "ops", "gating_policy": "auto", "config_json": "{}"}, follow_redirects=False)
    run = client.post(f"/workflows/{workflow_id}/run?tenant_id=1", follow_redirects=False)
    print("workflow run:", run.status_code)

    time.sleep(0.6)

    brain = client.post("/brainstorm?tenant_id=1", data={"title": "Need more local leads"}, follow_redirects=False)
    session_id = int(brain.headers["location"].split("session_id=")[1])
    print("brainstorm session:", brain.status_code)

    page = client.get(f"/brainstorm?tenant_id=1&session_id={session_id}")
    print("brainstorm page:", page.status_code)

    conn = client.get("/connectors?tenant_id=1")
    print("connectors page:", conn.status_code)

    cal = client.post("/calendar-events?tenant_id=1", data={"title": "Demo Event", "event_date": str(date.today())}, follow_redirects=False)
    print("calendar event:", cal.status_code)

    mobile = client.get("/m?tenant_id=1")
    print("mobile page:", mobile.status_code)

    print("full demo completed")


if __name__ == "__main__":
    main()
