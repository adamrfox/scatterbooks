from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_librarian
from app.isbn_lookup import lookup_isbn
from app.models import User
from app.models.app_settings import resolve_google_books_api_key
from app.schemas.isbn import IsbnLookupResult

router = APIRouter(prefix="/api/isbn", tags=["isbn"])


def _normalize_isbn(raw: str) -> str:
    return raw.replace("-", "").replace(" ", "").strip()


@router.get("/{isbn}", response_model=IsbnLookupResult)
async def get_isbn_lookup(
    isbn: str, db: DBSession = Depends(get_db), _: User = Depends(require_librarian)
) -> IsbnLookupResult:
    normalized = _normalize_isbn(isbn)
    google_books_api_key, _source = resolve_google_books_api_key(db)
    result = await lookup_isbn(normalized, google_books_api_key)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No book found for that ISBN"
        )
    return result
