def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_feature1_command_palette_search_endpoint(client):
    _login(client, "owner@test.local", "pass1234")

    created = client.post(
        "/clients?tenant_id=1",
        data={"name": "Client A", "contact_name": "Alex", "contact_email": "alex@example.test"},
        follow_redirects=False,
    )
    assert created.status_code == 303

    search = client.get("/search?tenant_id=1&q=Client A")
    assert search.status_code == 200
    payload = search.json()
    assert "results" in payload
    assert "clients" in payload
    assert "projects" in payload
    assert "commands" in payload
    assert any(item["title"] == "Client A" and "/clients?tenant_id=1" in item["url"] for item in payload["results"])


def test_feature4_today_cockpit_sections_render(client):
    _login(client, "owner@test.local", "pass1234")
    page = client.get("/dashboard?tenant_id=1")
    assert page.status_code == 200
    assert "Decisions" in page.text
    assert "Threats" in page.text
    assert "Opportunities" in page.text
    assert "Intelligence Feed" in page.text


def test_feature3_decision_calendar_renders_week_grid(client):
    _login(client, "owner@test.local", "pass1234")
    page = client.get("/calendar?tenant_id=1")
    assert page.status_code == 200
    assert "Decision Calendar" in page.text
    assert "This Week (Mon-Sun)" in page.text
    assert "Upcoming (Next 14 Days)" in page.text


def test_client_quickview_endpoint(client):
    _login(client, "owner@test.local", "pass1234")
    create = client.post(
        "/clients?tenant_id=1",
        data={"name": "QV Co", "contact_name": "Pat", "contact_email": "pat@qv.test", "contact_phone": "+123"},
        follow_redirects=False,
    )
    assert create.status_code == 303
    page = client.get("/clients?tenant_id=1")
    assert page.status_code == 200
    search = client.get("/search?tenant_id=1&q=QV Co")
    result = next(item for item in search.json()["clients"] if item["name"] == "QV Co")
    qv = client.get(f"/clients/{result['id']}/quickview?tenant_id=1")
    assert qv.status_code == 200
    payload = qv.json()
    assert payload["name"] == "QV Co"
