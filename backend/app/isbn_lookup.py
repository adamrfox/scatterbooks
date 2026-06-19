import httpx

from app.config import settings
from app.schemas.isbn import IsbnLookupResult

OPEN_LIBRARY_URL = "https://openlibrary.org/api/books"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
REQUEST_TIMEOUT = 6.0


async def _query_open_library(isbn: str) -> IsbnLookupResult | None:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            OPEN_LIBRARY_URL,
            params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
        )
    response.raise_for_status()
    data = response.json()
    book = data.get(f"ISBN:{isbn}")
    if not book:
        return None

    title = book.get("title")
    authors = book.get("authors") or []
    author = ", ".join(a["name"] for a in authors if a.get("name")) or None
    if not title and not author:
        return None
    return IsbnLookupResult(isbn=isbn, title=title, author=author)


async def _query_google_books(isbn: str) -> IsbnLookupResult | None:
    # Unauthenticated Google Books requests share a heavily-throttled default
    # quota that is, in practice, frequently already exhausted -- skip this
    # provider entirely unless the deployer configured their own (free) key.
    if not settings.google_books_api_key:
        return None

    params = {"q": f"isbn:{isbn}", "key": settings.google_books_api_key}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(GOOGLE_BOOKS_URL, params=params)
    response.raise_for_status()
    data = response.json()
    items = data.get("items") or []
    if not items:
        return None

    volume_info = items[0].get("volumeInfo", {})

    # Google Books' q=isbn:... is a search query, not a strict key lookup --
    # it can return an unrelated "closest match" instead of no result at all.
    # Only trust the result if the requested ISBN actually appears among the
    # item's own identifiers.
    identifiers = volume_info.get("industryIdentifiers") or []
    if not any(identifier.get("identifier") == isbn for identifier in identifiers):
        return None

    title = volume_info.get("title")
    authors = volume_info.get("authors") or []
    author = ", ".join(authors) or None
    if not title and not author:
        return None
    return IsbnLookupResult(isbn=isbn, title=title, author=author)


async def lookup_isbn(isbn: str) -> IsbnLookupResult | None:
    """Try Open Library first (no API key ever required), then Google Books
    (only if a key is configured -- see _query_google_books). A provider
    that errors or times out is skipped rather than failing the lookup.
    """
    for query in (_query_open_library, _query_google_books):
        try:
            result = await query(isbn)
        except httpx.HTTPError:
            continue
        if result is not None:
            return result
    return None
