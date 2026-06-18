from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.deps import SESSION_COOKIE_NAME, get_current_user
from app.models import Session, User
from app.schemas.user import LoginRequest, UserOut
from app.security import generate_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(
    body: LoginRequest, request: Request, response: Response, db: DBSession = Depends(get_db)
) -> User:
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    now = datetime.now(timezone.utc)
    session = Session(
        id=generate_session_token(),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(days=settings.session_ttl_days),
        last_seen_at=now,
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=settings.session_max_ttl_days * 24 * 3600,
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    sb_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if sb_session:
        db.query(Session).filter(Session.id == sb_session).delete()
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
