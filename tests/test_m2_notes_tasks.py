from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import Attachment, Note


def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_create_note_and_task_show_in_today_queue(client):
    _login(client, "owner@test.local", "pass1234")

    create_note = client.post(
        "/notes?tenant_id=1",
        data={"title": "Weekly Plan", "body_markdown": "# Plan\n- publish ad set"},
        follow_redirects=False,
    )
    assert create_note.status_code == 303

    create_task = client.post(
        "/tasks?tenant_id=1",
        data={"title": "Call client", "due_date": str(date.today()), "status": "todo"},
        follow_redirects=False,
    )
    assert create_task.status_code == 303

    notes_page = client.get("/notes?tenant_id=1")
    assert "Weekly Plan" in notes_page.text

    tasks_page = client.get("/tasks?tenant_id=1")
    assert "Call client" in tasks_page.text
    assert "Today Queue" in tasks_page.text


def test_attachment_is_tenant_scoped(client):
    _login(client, "owner@test.local", "pass1234")

    create_note = client.post(
        "/notes?tenant_id=2",
        data={"title": "Private Tenant2 Note", "body_markdown": "secret"},
        follow_redirects=False,
    )
    assert create_note.status_code == 303

    db = app.state.testing_sessionmaker()
    try:
        note = db.query(Note).filter(Note.title == "Private Tenant2 Note", Note.tenant_id == 2).first()
        assert note is not None
        upload = client.post(
            f"/notes/{note.id}/attachments?tenant_id=2",
            files={"file": ("secret.txt", b"tenant2 data", "text/plain")},
            follow_redirects=False,
        )
        assert upload.status_code == 303

        attachment = db.query(Attachment).filter(Attachment.note_id == note.id, Attachment.tenant_id == 2).first()
        assert attachment is not None
    finally:
        db.close()

    with TestClient(app) as viewer:
        viewer.post(
            "/login",
            data={"email": "viewer@test.local", "password": "pass1234"},
            follow_redirects=False,
        )
        denied = viewer.get(f"/attachments/{attachment.id}/download?tenant_id=1")
        assert denied.status_code == 404
