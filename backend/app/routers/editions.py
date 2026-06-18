from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_librarian, require_user
from app.models import Book, Edition, User
from app.schemas.edition import EditionCreate, EditionOut, EditionUpdate

router = APIRouter(prefix="/api/editions", tags=["editions"])


def _get_edition_or_404(db: DBSession, edition_id: int) -> Edition:
    edition = db.get(Edition, edition_id)
    if edition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found")
    return edition


@router.get("", response_model=list[EditionOut])
def list_editions(
    db: DBSession = Depends(get_db), _: User = Depends(require_user)
) -> list[Edition]:
    return db.query(Edition).order_by(Edition.name).all()


@router.post("", response_model=EditionOut, status_code=status.HTTP_201_CREATED)
def create_edition(
    body: EditionCreate, db: DBSession = Depends(get_db), _: User = Depends(require_librarian)
) -> Edition:
    if db.query(Edition).filter(Edition.name == body.name).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Edition already exists")
    edition = Edition(name=body.name)
    db.add(edition)
    db.commit()
    db.refresh(edition)
    return edition


@router.patch("/{edition_id}", response_model=EditionOut)
def rename_edition(
    edition_id: int,
    body: EditionUpdate,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> Edition:
    edition = _get_edition_or_404(db, edition_id)

    existing = db.query(Edition).filter(Edition.name == body.name).first()
    if existing is not None and existing.id != edition_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Edition already exists")

    edition.name = body.name
    db.flush()
    db.execute(
        text(
            "UPDATE books_fts SET edition_name = :name "
            "WHERE rowid IN (SELECT id FROM books WHERE edition_id = :edition_id)"
        ),
        {"name": body.name, "edition_id": edition_id},
    )
    db.commit()
    db.refresh(edition)
    return edition


@router.delete("/{edition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edition(
    edition_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_librarian)
) -> None:
    edition = _get_edition_or_404(db, edition_id)

    in_use = db.query(Book).filter(Book.edition_id == edition_id).first() is not None
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Edition is in use by one or more books",
        )

    db.delete(edition)
    db.commit()
