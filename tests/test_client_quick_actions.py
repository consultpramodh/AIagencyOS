def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_client_contact_quick_actions_render(client):
    _login(client, "owner@test.local", "pass1234")

    create = client.post(
        "/clients?tenant_id=1",
        data={
            "name": "Quick Action Co",
            "contact_name": "Sam",
            "contact_email": "sam@quick.test",
            "contact_phone": "+15552223333",
        },
        follow_redirects=False,
    )
    assert create.status_code == 303

    page = client.get("/clients?tenant_id=1")
    assert "tel:+15552223333" in page.text
    assert "mailto:sam@quick.test" in page.text
    assert "sms:+15552223333" in page.text
