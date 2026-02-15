import os
import sys
from datetime import date

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


def main() -> None:
    client = TestClient(app)

    owner_login = client.post(
        "/login",
        data={"email": "owner@demo.local", "password": "demo1234"},
        follow_redirects=False,
    )
    print("Owner login:", owner_login.status_code)

    note_resp = client.post(
        "/notes?tenant_id=1",
        data={"title": "Demo M2 Note", "body_markdown": "# Demo\nThis is an editable note."},
        follow_redirects=False,
    )
    print("Create note:", note_resp.status_code)

    task_resp = client.post(
        "/tasks?tenant_id=1",
        data={"title": "Demo M2 Task", "due_date": str(date.today()), "status": "todo"},
        follow_redirects=False,
    )
    print("Create task:", task_resp.status_code)

    notes_page = client.get("/notes?tenant_id=1")
    tasks_page = client.get("/tasks?tenant_id=1")
    print("Notes load:", notes_page.status_code)
    print("Tasks load:", tasks_page.status_code)
    print("Contains note:", "Demo M2 Note" in notes_page.text)
    print("Contains task:", "Demo M2 Task" in tasks_page.text)
    print("Contains Today Queue:", "Today Queue" in tasks_page.text)

    print("M2 demo completed")


if __name__ == "__main__":
    main()
