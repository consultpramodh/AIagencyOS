from functools import lru_cache
import os


class Settings:
    app_name: str = "AI Marketing Agency OS"
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./agency_os.db")
    session_cookie: str = "agency_os_session"


@lru_cache
def get_settings() -> Settings:
    return Settings()
