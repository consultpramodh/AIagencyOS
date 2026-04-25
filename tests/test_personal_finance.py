from datetime import date


def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_owner_can_track_personal_finance_plan(client):
    _login(client, "owner@test.local", "pass1234")

    account = client.post(
        "/finance/accounts?tenant_id=1",
        data={"name": "Main Checking", "account_type": "checking", "institution": "Demo Bank", "balance": "2500"},
        follow_redirects=False,
    )
    assert account.status_code == 303

    goal = client.post(
        "/finance/goals?tenant_id=1",
        data={"title": "Emergency Fund", "target_amount": "10000", "current_amount": "2500", "target_date": str(date.today())},
        follow_redirects=False,
    )
    assert goal.status_code == 303

    tx = client.post(
        "/finance/transactions?tenant_id=1",
        data={
            "account_id": "1",
            "transaction_date": str(date.today()),
            "category": "Salary",
            "description": "Monthly paycheck",
            "amount": "4000",
            "transaction_kind": "income",
        },
        follow_redirects=False,
    )
    assert tx.status_code == 303

    page = client.get("/finance?tenant_id=1")
    assert page.status_code == 200
    assert "Main Checking" in page.text
    assert "Emergency Fund" in page.text
    assert "Monthly paycheck" in page.text


def test_viewer_cannot_add_finance_records(client):
    _login(client, "viewer@test.local", "pass1234")

    response = client.post(
        "/finance/accounts?tenant_id=1",
        data={"name": "Should Fail", "account_type": "checking", "institution": "Bank", "balance": "100"},
        follow_redirects=False,
    )
    assert response.status_code == 403
