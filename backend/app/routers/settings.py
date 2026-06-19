from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_admin
from app.models import User
from app.models.app_settings import get_app_settings, resolve_google_books_api_key
from app.schemas.settings import AppSettingsOut, AppSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_out(db: DBSession) -> AppSettingsOut:
    api_key, source = resolve_google_books_api_key(db)
    return AppSettingsOut(
        google_books_api_key_configured=api_key is not None,
        google_books_api_key_source=source,
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
    row.google_books_api_key = body.google_books_api_key or None
    db.commit()
    return _to_out(db)
