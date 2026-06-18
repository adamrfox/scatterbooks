from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.models import Session, User

SESSION_COOKIE_NAME = "sb_session"


def get_current_user(
    sb_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: DBSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )
    if not sb_session:
        raise unauthorized

    session = db.get(Session, sb_session)
    now = datetime.now(timezone.utc)
    if session is None or session.expires_at.replace(tzinfo=timezone.utc) < now:
        raise unauthorized

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise unauthorized

    created_at = session.created_at.replace(tzinfo=timezone.utc)
    max_expiry = created_at + timedelta(days=settings.session_max_ttl_days)
    sliding_expiry = now + timedelta(days=settings.session_ttl_days)
    session.expires_at = min(sliding_expiry, max_expiry)
    session.last_seen_at = now
    db.commit()

    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return checker


require_user = require_role("user", "librarian", "admin")
require_librarian = require_role("librarian", "admin")
require_admin = require_role("admin")
