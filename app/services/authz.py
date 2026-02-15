from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.session import read_session
from app.models import Membership, Tenant, User


@dataclass
class CurrentContext:
    user: User
    tenant: Tenant
    membership: Membership


def _find_current_user(request: Request, db: Session) -> User:
    user_id = read_session(request)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user


def require_context(request: Request, db: Session = Depends(get_db)) -> CurrentContext:
    user = _find_current_user(request, db)
    memberships = (
        db.query(Membership)
        .filter(Membership.user_id == user.id)
        .order_by(Membership.id.asc())
        .all()
    )
    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant membership")

    requested_tenant = request.query_params.get("tenant_id")
    membership = memberships[0]
    if requested_tenant:
        for m in memberships:
            if m.tenant_id == int(requested_tenant):
                membership = m
                break
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")

    tenant = db.query(Tenant).filter(Tenant.id == membership.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant unavailable")

    return CurrentContext(user=user, tenant=tenant, membership=membership)


def require_role(min_role: str):
    role_order = {"viewer": 1, "admin": 2, "owner": 3}

    def _dep(ctx: CurrentContext = Depends(require_context)) -> CurrentContext:
        if role_order.get(ctx.membership.role, 0) < role_order.get(min_role, 0):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx

    return _dep
