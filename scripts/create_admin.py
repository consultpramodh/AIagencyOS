import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Membership, Tenant, User


def run(email: str, password: str, tenant_name: str):
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
        if not tenant:
            tenant = Tenant(name=tenant_name)
            db.add(tenant)
            db.flush()

        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            user = User(email=email.lower().strip(), full_name="Admin User", password_hash=hash_password(password))
            db.add(user)
            db.flush()

        membership = (
            db.query(Membership)
            .filter(Membership.user_id == user.id, Membership.tenant_id == tenant.id)
            .first()
        )
        if not membership:
            db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="owner"))

        db.commit()
        print(f"Admin ready: {email} @ {tenant.name}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--tenant", default="Default Tenant")
    args = parser.parse_args()
    run(args.email, args.password, args.tenant)
