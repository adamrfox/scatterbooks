from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_librarian, require_user
from app.images import delete_book_image_directory
from app.models import Book, Category, Edition, User
from app.schemas.book import BookCreate, BookOut, BookUpdate

router = APIRouter(prefix="/api/books", tags=["books"])


def _validate_refs(db: DBSession, category_id: int | None, edition_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id not found")
    if edition_id is not None and db.get(Edition, edition_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="edition_id not found")


def _get_book_or_404(db: DBSession, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


def _build_fts_match(q: str) -> str | None:
    """Turn free text into an FTS5 MATCH expression: each whitespace-separated
    token becomes a quoted prefix term (so partial words match as you type),
    quote-escaped so stray punctuation can't break FTS5's query syntax. Space
    between terms is FTS5's implicit AND, so all tokens must match.
    """
    tokens = q.strip().split()
    if not tokens:
        return None
    return " ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)


def _search_books(
    db: DBSession,
    fts_query: str,
    category_id: int | None,
    edition_id: int | None,
    limit: int,
    offset: int,
) -> list[Book]:
    rows = db.execute(
        text(
            "SELECT b.id FROM books b "
            "JOIN books_fts ON books_fts.rowid = b.id "
            "WHERE books_fts MATCH :fts_query "
            "AND (:category_id IS NULL OR b.category_id = :category_id) "
            "AND (:edition_id IS NULL OR b.edition_id = :edition_id) "
            "ORDER BY bm25(books_fts) "
            "LIMIT :limit OFFSET :offset"
        ),
        {
            "fts_query": fts_query,
            "category_id": category_id,
            "edition_id": edition_id,
            "limit": limit,
            "offset": offset,
        },
    ).all()
    ordered_ids = [row[0] for row in rows]
    if not ordered_ids:
        return []
    books_by_id = {book.id: book for book in db.query(Book).filter(Book.id.in_(ordered_ids)).all()}
    return [books_by_id[book_id] for book_id in ordered_ids if book_id in books_by_id]


@router.get("", response_model=list[BookOut])
def list_books(
    q: str | None = None,
    category_id: int | None = None,
    edition_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_db),
    _: User = Depends(require_user),
) -> list[Book]:
    fts_query = _build_fts_match(q) if q else None
    if fts_query:
        return _search_books(db, fts_query, category_id, edition_id, limit, offset)

    query = db.query(Book)
    if category_id is not None:
        query = query.filter(Book.category_id == category_id)
    if edition_id is not None:
        query = query.filter(Book.edition_id == edition_id)
    return query.order_by(Book.title).offset(offset).limit(limit).all()


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    body: BookCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_librarian),
) -> Book:
    _validate_refs(db, body.category_id, body.edition_id)
    book = Book(
        title=body.title,
        author=body.author,
        category_id=body.category_id,
        edition_id=body.edition_id,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("/{book_id}", response_model=BookOut)
def get_book(
    book_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_user)
) -> Book:
    return _get_book_or_404(db, book_id)


@router.patch("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    body: BookUpdate,
    db: DBSession = Depends(get_db),
    _: User = Depends(require_librarian),
) -> Book:
    book = _get_book_or_404(db, book_id)
    updates = body.model_dump(exclude_unset=True)

    _validate_refs(
        db,
        updates.get("category_id", book.category_id),
        updates.get("edition_id", book.edition_id),
    )

    for field, value in updates.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int, db: DBSession = Depends(get_db), _: User = Depends(require_librarian)
) -> None:
    book = _get_book_or_404(db, book_id)
    db.delete(book)
    db.commit()
    delete_book_image_directory(book_id)
