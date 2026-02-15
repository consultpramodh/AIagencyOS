from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import Membership, Tenant, User


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    tenant_a = Tenant(name="Tenant A")
    tenant_b = Tenant(name="Tenant B")
    db.add_all([tenant_a, tenant_b])
    db.flush()

    owner = User(email="owner@test.local", full_name="Owner", password_hash=hash_password("pass1234"))
    viewer = User(email="viewer@test.local", full_name="Viewer", password_hash=hash_password("pass1234"))
    db.add_all([owner, viewer])
    db.flush()

    db.add_all(
        [
            Membership(tenant_id=tenant_a.id, user_id=owner.id, role="owner"),
            Membership(tenant_id=tenant_b.id, user_id=owner.id, role="admin"),
            Membership(tenant_id=tenant_a.id, user_id=viewer.id, role="viewer"),
        ]
    )
    db.commit()
    db.close()

    def override_get_db():
        test_db = TestingSessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
