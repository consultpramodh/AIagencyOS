from app.main import app
from app.models import BrainstormQA, Recommendation, WorkflowTemplate


def _login(client, email, password):
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_brainstorm_generates_recommendation_and_workflow(client):
    _login(client, "owner@test.local", "pass1234")

    session_resp = client.post("/brainstorm?tenant_id=1", data={"title": "Need more leads"}, follow_redirects=False)
    assert session_resp.status_code == 303
    session_id = int(session_resp.headers["location"].split("session_id=")[1])

    page = client.get(f"/brainstorm?tenant_id=1&session_id={session_id}")
    assert page.status_code == 200

    # answer first two questions heuristically
    db = app.state.testing_sessionmaker()
    try:
        qas = db.query(BrainstormQA).filter(BrainstormQA.session_id == session_id, BrainstormQA.tenant_id == 1).order_by(BrainstormQA.question_order.asc()).all()
    finally:
        db.close()

    for qa in qas[:2]:
        client.post(f"/brainstorm/{session_id}/answers/{qa.id}?tenant_id=1", data={"answer": "SEO and Ads"}, follow_redirects=False)

    rec_resp = client.post(f"/brainstorm/{session_id}/recommend?tenant_id=1", follow_redirects=False)
    assert rec_resp.status_code == 303

    db = app.state.testing_sessionmaker()
    try:
        rec = db.query(Recommendation).filter(Recommendation.session_id == session_id, Recommendation.tenant_id == 1).first()
        assert rec is not None
    finally:
        db.close()

    wf_resp = client.post(f"/brainstorm/{session_id}/create-workflow?tenant_id=1", follow_redirects=False)
    assert wf_resp.status_code == 303

    db = app.state.testing_sessionmaker()
    try:
        wf = db.query(WorkflowTemplate).filter(WorkflowTemplate.tenant_id == 1, WorkflowTemplate.name.like("Brainstorm:%")).first()
        assert wf is not None
    finally:
        db.close()
