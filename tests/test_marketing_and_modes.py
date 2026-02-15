def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def _create_client(client, name="Acme Dental"):
    response = client.post(
        "/clients?tenant_id=1",
        data={"name": name, "contact_name": "Owner", "contact_email": "owner@example.test"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_dashboard_mode_toggle_renders_client_dashboard(client):
    _login(client, "owner@test.local", "pass1234")
    _create_client(client, "Mode Client")

    page = client.get("/dashboard?tenant_id=1&mode=client")
    assert page.status_code == 200
    assert "Client Dashboard" in page.text
    assert "Mode Client" in page.text
    assert "mode=admin" in page.text
    assert "mode=client" in page.text


def test_marketing_campaign_planner_and_save(client):
    _login(client, "owner@test.local", "pass1234")
    _create_client(client, "Acme Dental")

    search = client.get("/search?tenant_id=1&q=Acme Dental")
    client_id = next(item["id"] for item in search.json()["clients"] if item["name"] == "Acme Dental")

    preview = client.post(
        "/marketing/plan?tenant_id=1",
        data={
            "client_id": str(client_id),
            "platform": "Google Ads",
            "objective": "Lead Generation",
            "sub_option": "Search Leads",
            "template_name": "Local Lead Gen Search",
            "budget": "50",
            "days": "7",
            "existing_keywords": "acme dentist",
            "website_url": "https://acmedental.example",
            "social_handles": "@acmedental, @acmedentalcare",
        },
        follow_redirects=False,
    )
    assert preview.status_code == 200
    assert "3. Review Plan" in preview.text
    assert "SEO Content Pack" in preview.text
    assert "Title tag" in preview.text
    assert "Local Lead Gen Search" in preview.text
    assert "Daily Budget" in preview.text
    assert "acme near me" in preview.text.lower() or "dental near me" in preview.text.lower()

    create = client.post(
        "/marketing/campaigns?tenant_id=1",
        data={
            "name": "Google Leads Week 1",
            "client_id": str(client_id),
            "platform": "Google Ads",
            "objective": "Lead Generation",
            "sub_option": "Search Leads",
            "template_name": "Local Lead Gen Search",
            "budget": "50",
            "days": "7",
            "existing_keywords": "acme dentist",
            "website_url": "https://acmedental.example",
            "social_handles": "@acmedental, @acmedentalcare",
        },
        follow_redirects=False,
    )
    assert create.status_code == 303
    assert "/marketing?tenant_id=1&toast=campaign-created" in create.headers["location"]

    page = client.get("/marketing?tenant_id=1")
    assert page.status_code == 200
    assert "Google Leads Week 1" in page.text
