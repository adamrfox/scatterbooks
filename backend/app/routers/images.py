from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_librarian, require_user
from app.images import (
    ImageProcessingError,
    full_image_path,
    process_upload,
    thumb_image_path,
)
from app.models import Book, BookImage, User
from app.schemas.image import BookImageOut, BookImageReorder

router = APIRouter(prefix="/api/books/{book_id}/images", tags=["images"])

MAX_IMAGES_PER_BOOK = 5


def _get_book_or_404(db: DBSession, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


def _get_image_or_404(db: DBSession, book_id: int, image_id: int) -> BookImage:
    image = db.get(BookImage, image_id)
    if image is None or image.book_id != book_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


def _next_position(db: DBSession, book_id: int) -> int:
    used = {
        row[0]
        for row in db.query(BookImage.position).filter(BookImage.book_id == book_id).all()
    }
    for position in range(MAX_IMAGES_PER_BOOK):
        if position not in used:
            return position
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum 5 images per book")


@router.get("", response_model=list[BookImageOut])
def list_images(
    book_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_user)
) -> list[BookImage]:
    _get_book_or_404(db, book_id)
    return (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id)
        .order_by(BookImage.position)
        .all()
    )


@router.post("", response_model=BookImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    book_id: int,
    file: UploadFile,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> BookImage:
    _get_book_or_404(db, book_id)

    count = db.query(BookImage).filter(BookImage.book_id == book_id).count()
    if count >= MAX_IMAGES_PER_BOOK:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum 5 images per book")

    raw_bytes = await file.read()
    try:
        full_bytes, thumb_bytes, width, height = process_upload(raw_bytes)
    except ImageProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    position = _next_position(db, book_id)
    image = BookImage(
        book_id=book_id,
        position=position,
        filename="pending",
        content_type="image/jpeg",
        width=width,
        height=height,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    image.filename = f"{image.id}_full.jpg"
    db.commit()

    try:
        full_path = full_image_path(book_id, image.id)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(full_bytes)
        thumb_image_path(book_id, image.id).write_bytes(thumb_bytes)
    except OSError as exc:
        db.delete(image)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store image"
        ) from exc

    db.refresh(image)
    return image


@router.get("/{image_id}")
def get_full_image(
    book_id: int, image_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_user)
) -> FileResponse:
    image = _get_image_or_404(db, book_id, image_id)
    path = full_image_path(book_id, image_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing")
    return FileResponse(path, media_type=image.content_type)


@router.get("/{image_id}/thumb")
def get_thumb_image(
    book_id: int, image_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_user)
) -> FileResponse:
    image = _get_image_or_404(db, book_id, image_id)
    path = thumb_image_path(book_id, image_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing")
    return FileResponse(path, media_type=image.content_type)


@router.patch("/{image_id}", response_model=BookImageOut)
def reorder_image(
    book_id: int,
    image_id: int,
    body: BookImageReorder,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> BookImage:
    image = _get_image_or_404(db, book_id, image_id)

    if body.position != image.position:
        conflict = (
            db.query(BookImage)
            .filter(BookImage.book_id == book_id, BookImage.position == body.position)
            .first()
        )
        if conflict is not None:
            # Swap via a temporary out-of-range sentinel to avoid tripping the
            # UNIQUE(book_id, position) constraint while both rows are in flight.
            old_position = image.position
            image.position = -1
            db.flush()
            conflict.position = old_position
            db.flush()

        image.position = body.position

    db.commit()
    db.refresh(image)
    return image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    book_id: int,
    image_id: int,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> None:
    image = _get_image_or_404(db, book_id, image_id)

    full_path = full_image_path(book_id, image_id)
    thumb_path = thumb_image_path(book_id, image_id)
    db.delete(image)
    db.commit()

    full_path.unlink(missing_ok=True)
    thumb_path.unlink(missing_ok=True)
