def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_tenant_isolation_denies_unassigned_tenant(client):
    _login(client, "viewer@test.local", "pass1234")

    allowed = client.get("/?tenant_id=1")
    assert allowed.status_code == 200

    denied = client.get("/?tenant_id=2")
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Tenant access denied"


def test_viewer_cannot_create_client(client):
    _login(client, "viewer@test.local", "pass1234")

    response = client.post("/clients?tenant_id=1", data={"name": "Blocked Co"}, follow_redirects=False)
    assert response.status_code == 403


def test_owner_can_create_client(client):
    _login(client, "owner@test.local", "pass1234")

    response = client.post(
        "/clients?tenant_id=1",
        data={
            "name": "Allowed Co",
            "contact_name": "A Person",
            "contact_email": "a@co.test",
            "contact_phone": "+15550001111",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    page = client.get("/clients?tenant_id=1")
    assert "Allowed Co" in page.text
    assert "a@co.test" in page.text
