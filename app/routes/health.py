from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health/db")
def db_health():
    db = SessionLocal()
    try:
        db.execute(text("select 1"))
        return {"ok": True}
    except SQLAlchemyError as exc:
        detail = str(getattr(exc, "orig", exc)).splitlines()[0]
        return {"ok": False, "error": exc.__class__.__name__, "detail": detail[:240]}
    finally:
        db.close()
