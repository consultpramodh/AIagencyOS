from datetime import date


def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_owner_can_create_service_job_and_calendar_event(client):
    _login(client, "owner@test.local", "pass1234")

    job = client.post(
        "/service-jobs?tenant_id=1",
        data={"title": "Website Speed Fix", "service_type": "Web", "scheduled_for": str(date.today())},
        follow_redirects=False,
    )
    assert job.status_code == 303

    event = client.post(
        "/calendar-events?tenant_id=1",
        data={"title": "Standup", "event_date": str(date.today())},
        follow_redirects=False,
    )
    assert event.status_code == 303

    page = client.get("/?tenant_id=1")
    assert "Website Speed Fix" in page.text
    assert "Standup" in page.text


def test_viewer_cannot_create_service_job(client):
    _login(client, "viewer@test.local", "pass1234")
    response = client.post(
        "/service-jobs?tenant_id=1",
        data={"title": "Blocked Job", "service_type": "SEO"},
        follow_redirects=False,
    )
    assert response.status_code == 403
