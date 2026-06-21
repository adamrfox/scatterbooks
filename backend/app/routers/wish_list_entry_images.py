from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_user
from app.images import (
    ImageProcessingError,
    process_upload,
    wish_list_entry_full_image_path,
    wish_list_entry_thumb_image_path,
)
from app.models import User, WishList, WishListEntry, WishListEntryImage
from app.schemas.wish_list_entry_image import WishListEntryImageOut, WishListEntryImageReorder

router = APIRouter(
    prefix="/api/wish-lists/{wish_list_id}/entries/{entry_id}/images", tags=["wish-lists"]
)

MAX_IMAGES_PER_ENTRY = 5


def _is_owner_or_admin(user: User, wish_list: WishList) -> bool:
    return user.role == "admin" or wish_list.owner_id == user.id


def _is_visible(user: User, wish_list: WishList) -> bool:
    return wish_list.is_public or _is_owner_or_admin(user, wish_list)


def _get_visible_wish_list_or_404(db: DBSession, wish_list_id: int, user: User) -> WishList:
    wish_list = db.get(WishList, wish_list_id)
    if wish_list is None or not _is_visible(user, wish_list):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wish list not found")
    return wish_list


def _require_owner_or_admin(wish_list: WishList, user: User) -> None:
    if not _is_owner_or_admin(user, wish_list):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _get_entry_or_404(db: DBSession, wish_list: WishList, entry_id: int) -> WishListEntry:
    entry = db.get(WishListEntry, entry_id)
    if entry is None or entry.wish_list_id != wish_list.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wish list entry not found"
        )
    return entry


def _get_image_or_404(db: DBSession, entry_id: int, image_id: int) -> WishListEntryImage:
    image = db.get(WishListEntryImage, image_id)
    if image is None or image.wish_list_entry_id != entry_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


def _next_position(db: DBSession, entry_id: int) -> int:
    used = {
        row[0]
        for row in db.query(WishListEntryImage.position)
        .filter(WishListEntryImage.wish_list_entry_id == entry_id)
        .all()
    }
    for position in range(MAX_IMAGES_PER_ENTRY):
        if position not in used:
            return position
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum 5 images per entry")


@router.get("", response_model=list[WishListEntryImageOut])
def list_images(
    wish_list_id: int,
    entry_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> list[WishListEntryImage]:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    entry = _get_entry_or_404(db, wish_list, entry_id)
    return (
        db.query(WishListEntryImage)
        .filter(WishListEntryImage.wish_list_entry_id == entry.id)
        .order_by(WishListEntryImage.position)
        .all()
    )


@router.post("", response_model=WishListEntryImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    wish_list_id: int,
    entry_id: int,
    file: UploadFile,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> WishListEntryImage:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    entry = _get_entry_or_404(db, wish_list, entry_id)

    count = (
        db.query(WishListEntryImage)
        .filter(WishListEntryImage.wish_list_entry_id == entry.id)
        .count()
    )
    if count >= MAX_IMAGES_PER_ENTRY:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum 5 images per entry")

    raw_bytes = await file.read()
    try:
        full_bytes, thumb_bytes, width, height = process_upload(raw_bytes)
    except ImageProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    position = _next_position(db, entry.id)
    image = WishListEntryImage(
        wish_list_entry_id=entry.id,
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
        full_path = wish_list_entry_full_image_path(entry.id, image.id)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(full_bytes)
        wish_list_entry_thumb_image_path(entry.id, image.id).write_bytes(thumb_bytes)
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
    wish_list_id: int,
    entry_id: int,
    image_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> FileResponse:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _get_entry_or_404(db, wish_list, entry_id)
    image = _get_image_or_404(db, entry_id, image_id)
    path = wish_list_entry_full_image_path(entry_id, image_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing")
    return FileResponse(path, media_type=image.content_type)


@router.get("/{image_id}/thumb")
def get_thumb_image(
    wish_list_id: int,
    entry_id: int,
    image_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> FileResponse:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _get_entry_or_404(db, wish_list, entry_id)
    image = _get_image_or_404(db, entry_id, image_id)
    path = wish_list_entry_thumb_image_path(entry_id, image_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing")
    return FileResponse(path, media_type=image.content_type)


@router.patch("/{image_id}", response_model=WishListEntryImageOut)
def reorder_image(
    wish_list_id: int,
    entry_id: int,
    image_id: int,
    body: WishListEntryImageReorder,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> WishListEntryImage:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    _get_entry_or_404(db, wish_list, entry_id)
    image = _get_image_or_404(db, entry_id, image_id)

    if body.position != image.position:
        conflict = (
            db.query(WishListEntryImage)
            .filter(
                WishListEntryImage.wish_list_entry_id == entry_id,
                WishListEntryImage.position == body.position,
            )
            .first()
        )
        if conflict is not None:
            # Swap via a temporary out-of-range sentinel to avoid tripping the
            # UNIQUE(wish_list_entry_id, position) constraint while both rows
            # are in flight.
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
    wish_list_id: int,
    entry_id: int,
    image_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> None:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    _get_entry_or_404(db, wish_list, entry_id)
    image = _get_image_or_404(db, entry_id, image_id)

    full_path = wish_list_entry_full_image_path(entry_id, image_id)
    thumb_path = wish_list_entry_thumb_image_path(entry_id, image_id)
    db.delete(image)
    db.commit()

    full_path.unlink(missing_ok=True)
    thumb_path.unlink(missing_ok=True)
