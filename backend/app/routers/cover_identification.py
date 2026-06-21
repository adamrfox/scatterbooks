import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.cover_identification import CoverIdentificationError, identify_book_from_photo
from app.database import get_db
from app.deps import require_librarian
from app.images import ImageProcessingError, prepare_for_identification
from app.models import User
from app.models.app_settings import resolve_anthropic_api_key
from app.schemas.cover_identification import IdentifyCoverResult

router = APIRouter(prefix="/api/identify-cover", tags=["identify-cover"])


@router.post("", response_model=IdentifyCoverResult)
async def identify_cover(
    file: UploadFile,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> IdentifyCoverResult:
    api_key, _source = resolve_anthropic_api_key(db)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI cover identification isn't configured for this library.",
        )

    raw_bytes = await file.read()
    try:
        prepared = prepare_for_identification(raw_bytes)
    except ImageProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        return await identify_book_from_photo(prepared, api_key)
    except (httpx.HTTPError, CoverIdentificationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not identify the book from that photo. Try manual entry.",
        ) from exc
