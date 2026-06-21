from typing import Literal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config import settings as env_settings
from app.database import Base

SINGLETON_ID = 1

KeySource = Literal["database", "environment", "none"]


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_books_api_key: Mapped[str | None] = mapped_column(String(255))
    anthropic_api_key: Mapped[str | None] = mapped_column(String(255))


def get_app_settings(db: Session) -> AppSettings:
    row = db.get(AppSettings, SINGLETON_ID)
    if row is None:
        # Should always exist after the migration seeds it, but don't 500 if
        # it's somehow missing -- just create it on the fly.
        row = AppSettings(id=SINGLETON_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _resolve(db_value: str | None, env_value: str | None) -> tuple[str | None, KeySource]:
    if db_value:
        return db_value, "database"
    if env_value:
        return env_value, "environment"
    return None, "none"


def resolve_google_books_api_key(db: Session) -> tuple[str | None, KeySource]:
    """Database value wins; falls back to the GOOGLE_BOOKS_API_KEY env var."""
    row = get_app_settings(db)
    return _resolve(row.google_books_api_key, env_settings.google_books_api_key)


def resolve_anthropic_api_key(db: Session) -> tuple[str | None, KeySource]:
    """Database value wins; falls back to the ANTHROPIC_API_KEY env var."""
    row = get_app_settings(db)
    return _resolve(row.anthropic_api_key, env_settings.anthropic_api_key)
