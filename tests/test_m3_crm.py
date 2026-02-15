from app.main import app
from app.models import Client, Deal, DealStage


def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_crm_deal_pipeline_and_tenant_boundary(client):
    _login(client, "owner@test.local", "pass1234")

    client.post(
        "/clients?tenant_id=1",
        data={"name": "CRM Client", "contact_name": "Amy", "contact_email": "amy@test.local", "contact_phone": "+10000001"},
        follow_redirects=False,
    )

    db = app.state.testing_sessionmaker()
    client_id = None
    stage_id = None
    try:
        c = db.query(Client).filter(Client.name == "CRM Client", Client.tenant_id == 1).first()
        assert c is not None
        client_id = c.id
        stage = DealStage(tenant_id=1, name="Lead", position=1)
        db.add(stage)
        db.commit()
        db.refresh(stage)
        stage_id = stage.id
    finally:
        db.close()

    deal_resp = client.post(
        "/crm/deals?tenant_id=1",
        data={"client_id": client_id, "title": "Retainer", "value_cents": 120000, "stage_id": stage_id},
        follow_redirects=False,
    )
    assert deal_resp.status_code == 303

    db = app.state.testing_sessionmaker()
    try:
        deal = db.query(Deal).filter(Deal.tenant_id == 1, Deal.title == "Retainer").first()
        assert deal is not None
    finally:
        db.close()

    viewer = client.__class__(app)
    viewer.post("/login", data={"email": "viewer@test.local", "password": "pass1234"}, follow_redirects=False)
    denied = viewer.post(
        "/crm/deals?tenant_id=2",
        data={"client_id": client_id, "title": "Cross Tenant", "value_cents": 1000, "stage_id": stage_id},
        follow_redirects=False,
    )
    assert denied.status_code in {403, 404}
