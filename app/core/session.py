from fastapi import Request, Response
from itsdangerous import URLSafeSerializer

from app.core.config import get_settings

settings = get_settings()
serializer = URLSafeSerializer(settings.secret_key, salt="session")


def set_session(response: Response, user_id: int) -> None:
    signed = serializer.dumps({"user_id": user_id})
    response.set_cookie(
        settings.session_cookie,
        signed,
        httponly=True,
        secure=False,
        samesite="lax",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(settings.session_cookie)


def read_session(request: Request) -> int | None:
    raw = request.cookies.get(settings.session_cookie)
    if not raw:
        return None
    try:
        payload = serializer.loads(raw)
        return int(payload.get("user_id"))
    except Exception:
        return None
