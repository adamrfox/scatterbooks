from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_librarian, require_user
from app.images import (
    delete_wish_list_entry_image_directory,
    full_image_path,
    thumb_image_path,
    wish_list_entry_full_image_path,
    wish_list_entry_thumb_image_path,
)
from app.models import Book, BookImage, Category, Edition, User, WishList, WishListEntry
from app.schemas.book import BookOut
from app.schemas.wish_list import (
    WishListCreate,
    WishListEntryCreate,
    WishListEntryOut,
    WishListEntryUpdate,
    WishListOut,
    WishListUpdate,
)

router = APIRouter(prefix="/api/wish-lists", tags=["wish-lists"])


def _is_owner_or_admin(user: User, wish_list: WishList) -> bool:
    return user.role == "admin" or wish_list.owner_id == user.id


def _is_visible(user: User, wish_list: WishList) -> bool:
    return wish_list.is_public or _is_owner_or_admin(user, wish_list)


def _get_visible_wish_list_or_404(db: DBSession, wish_list_id: int, user: User) -> WishList:
    # A private list a caller isn't entitled to see returns 404, same as a
    # missing one -- a 403 would leak that the list exists.
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


def _validate_refs(db: DBSession, category_id: int | None, edition_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id not found")
    if edition_id is not None and db.get(Edition, edition_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="edition_id not found")


@router.get("", response_model=list[WishListOut])
def list_wish_lists(
    db: DBSession = Depends(get_db), user: User = Depends(require_user)
) -> list[WishList]:
    query = db.query(WishList)
    if user.role != "admin":
        query = query.filter((WishList.is_public.is_(True)) | (WishList.owner_id == user.id))
    return query.order_by(WishList.name).all()


@router.post("", response_model=WishListOut, status_code=status.HTTP_201_CREATED)
def create_wish_list(
    body: WishListCreate, db: DBSession = Depends(get_db), user: User = Depends(require_librarian)
) -> WishList:
    wish_list = WishList(name=body.name, is_public=body.is_public, owner_id=user.id)
    db.add(wish_list)
    db.commit()
    db.refresh(wish_list)
    return wish_list


@router.get("/{wish_list_id}", response_model=WishListOut)
def get_wish_list(
    wish_list_id: int, db: DBSession = Depends(get_db), user: User = Depends(require_user)
) -> WishList:
    return _get_visible_wish_list_or_404(db, wish_list_id, user)


@router.patch("/{wish_list_id}", response_model=WishListOut)
def update_wish_list(
    wish_list_id: int,
    body: WishListUpdate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> WishList:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(wish_list, field, value)

    db.commit()
    db.refresh(wish_list)
    return wish_list


@router.delete("/{wish_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wish_list(
    wish_list_id: int, db: DBSession = Depends(get_db), user: User = Depends(require_user)
) -> None:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)

    entry_ids = [entry.id for entry in wish_list.entries]
    db.delete(wish_list)
    db.commit()

    for entry_id in entry_ids:
        delete_wish_list_entry_image_directory(entry_id)


@router.get("/{wish_list_id}/entries", response_model=list[WishListEntryOut])
def list_entries(
    wish_list_id: int, db: DBSession = Depends(get_db), user: User = Depends(require_user)
) -> list[WishListEntry]:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    return (
        db.query(WishListEntry)
        .filter(WishListEntry.wish_list_id == wish_list.id)
        .order_by(WishListEntry.title)
        .all()
    )


@router.post(
    "/{wish_list_id}/entries", response_model=WishListEntryOut, status_code=status.HTTP_201_CREATED
)
def create_entry(
    wish_list_id: int,
    body: WishListEntryCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> WishListEntry:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    _validate_refs(db, body.category_id, body.edition_id)

    entry = WishListEntry(
        wish_list_id=wish_list.id,
        title=body.title,
        author=body.author,
        category_id=body.category_id,
        edition_id=body.edition_id,
        notes=body.notes,
        year=body.year,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{wish_list_id}/entries/{entry_id}", response_model=WishListEntryOut)
def get_entry(
    wish_list_id: int,
    entry_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> WishListEntry:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    return _get_entry_or_404(db, wish_list, entry_id)


@router.patch("/{wish_list_id}/entries/{entry_id}", response_model=WishListEntryOut)
def update_entry(
    wish_list_id: int,
    entry_id: int,
    body: WishListEntryUpdate,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> WishListEntry:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    entry = _get_entry_or_404(db, wish_list, entry_id)

    updates = body.model_dump(exclude_unset=True)
    _validate_refs(
        db,
        updates.get("category_id", entry.category_id),
        updates.get("edition_id", entry.edition_id),
    )

    for field, value in updates.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{wish_list_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    wish_list_id: int,
    entry_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> None:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    entry = _get_entry_or_404(db, wish_list, entry_id)

    db.delete(entry)
    db.commit()
    delete_wish_list_entry_image_directory(entry_id)


@router.post(
    "/{wish_list_id}/entries/{entry_id}/move-to-library",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
)
def move_entry_to_library(
    wish_list_id: int,
    entry_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(require_user),
) -> Book:
    wish_list = _get_visible_wish_list_or_404(db, wish_list_id, user)
    _require_owner_or_admin(wish_list, user)
    entry = _get_entry_or_404(db, wish_list, entry_id)

    book = Book(
        title=entry.title,
        author=entry.author,
        category_id=entry.category_id,
        edition_id=entry.edition_id,
        notes=entry.notes,
        year=entry.year,
        created_by=user.id,
    )
    db.add(book)
    db.flush()  # assigns book.id without committing -- the whole move is one transaction

    try:
        for image in entry.images:
            full_bytes = wish_list_entry_full_image_path(entry_id, image.id).read_bytes()
            thumb_bytes = wish_list_entry_thumb_image_path(entry_id, image.id).read_bytes()

            new_image = BookImage(
                book_id=book.id,
                position=image.position,
                filename="pending",
                content_type=image.content_type,
                width=image.width,
                height=image.height,
            )
            db.add(new_image)
            db.flush()
            new_image.filename = f"{new_image.id}_full.jpg"

            full_path = full_image_path(book.id, new_image.id)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(full_bytes)
            thumb_image_path(book.id, new_image.id).write_bytes(thumb_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy photos to the new book",
        ) from exc

    db.delete(entry)
    db.commit()
    db.refresh(book)

    delete_wish_list_entry_image_directory(entry_id)

    return book
