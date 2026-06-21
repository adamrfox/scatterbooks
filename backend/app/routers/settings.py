from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_admin
from app.models import User
from app.models.app_settings import (
    get_app_settings,
    resolve_anthropic_api_key,
    resolve_google_books_api_key,
)
from app.schemas.settings import AppSettingsOut, AppSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_out(db: DBSession) -> AppSettingsOut:
    google_books_key, google_books_source = resolve_google_books_api_key(db)
    anthropic_key, anthropic_source = resolve_anthropic_api_key(db)
    return AppSettingsOut(
        google_books_api_key_configured=google_books_key is not None,
        google_books_api_key_source=google_books_source,
        anthropic_api_key_configured=anthropic_key is not None,
        anthropic_api_key_source=anthropic_source,
    )


@router.get("", response_model=AppSettingsOut)
def get_settings(db: DBSession = Depends(get_db), _: User = Depends(require_admin)) -> AppSettingsOut:
    return _to_out(db)


@router.patch("", response_model=AppSettingsOut)
def update_settings(
    body: AppSettingsUpdate,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> AppSettingsOut:
    row = get_app_settings(db)
    # exclude_unset matters here: this endpoint has two independent secret
    # fields now, and a request that only mentions one must not blank the
    # other out by falling back to AppSettingsUpdate's default of None.
    updates = body.model_dump(exclude_unset=True)
    if "google_books_api_key" in updates:
        row.google_books_api_key = updates["google_books_api_key"] or None
    if "anthropic_api_key" in updates:
        row.anthropic_api_key = updates["anthropic_api_key"] or None
    db.commit()
    return _to_out(db)
