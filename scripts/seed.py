import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Client, Membership, Project, Tenant, User


def run() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "owner@demo.local").first():
            print("Seed already applied")
            return

        tenant_a = Tenant(name="Demo Agency")
        tenant_b = Tenant(name="Second Brand")
        db.add_all([tenant_a, tenant_b])
        db.flush()

        owner = User(email="owner@demo.local", full_name="Demo Owner", password_hash=hash_password("demo1234"))
        viewer = User(email="viewer@demo.local", full_name="Demo Viewer", password_hash=hash_password("demo1234"))
        db.add_all([owner, viewer])
        db.flush()

        db.add_all(
            [
                Membership(tenant_id=tenant_a.id, user_id=owner.id, role="owner"),
                Membership(tenant_id=tenant_b.id, user_id=owner.id, role="admin"),
                Membership(tenant_id=tenant_a.id, user_id=viewer.id, role="viewer"),
            ]
        )
        db.flush()

        client = Client(tenant_id=tenant_a.id, name="Acme Plumbing", status="active")
        db.add(client)
        db.flush()

        project = Project(tenant_id=tenant_a.id, client_id=client.id, name="Local SEO Sprint", status="planning")
        db.add(project)

        db.commit()
        print("Seeded demo tenant/user/client/project")
    finally:
        db.close()


if __name__ == "__main__":
    run()
