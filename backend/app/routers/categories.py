from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_librarian, require_user
from app.models import Book, Category, User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _get_category_or_404(db: DBSession, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: DBSession = Depends(get_db), _: User = Depends(require_user)
) -> list[Category]:
    return db.query(Category).order_by(Category.name).all()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate, db: DBSession = Depends(get_db), _: User = Depends(require_librarian)
) -> Category:
    if db.query(Category).filter(Category.name == body.name).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")
    category = Category(name=body.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
def rename_category(
    category_id: int,
    body: CategoryUpdate,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> Category:
    category = _get_category_or_404(db, category_id)

    existing = db.query(Category).filter(Category.name == body.name).first()
    if existing is not None and existing.id != category_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")

    category.name = body.name
    db.flush()
    db.execute(
        text(
            "UPDATE books_fts SET category_name = :name "
            "WHERE rowid IN (SELECT id FROM books WHERE category_id = :category_id)"
        ),
        {"name": body.name, "category_id": category_id},
    )
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_librarian)
) -> None:
    category = _get_category_or_404(db, category_id)

    in_use = db.query(Book).filter(Book.category_id == category_id).first() is not None
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category is in use by one or more books",
        )

    db.delete(category)
    db.commit()
