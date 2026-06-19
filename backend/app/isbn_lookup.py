import httpx

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


async def _query_google_books(isbn: str, api_key: str | None) -> IsbnLookupResult | None:
    # Unauthenticated Google Books requests share a heavily-throttled default
    # quota that is, in practice, frequently already exhausted -- skip this
    # provider entirely unless an API key was resolved (database or env var).
    if not api_key:
        return None

    params = {"q": f"isbn:{isbn}", "key": api_key}
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


async def lookup_isbn(isbn: str, google_books_api_key: str | None) -> IsbnLookupResult | None:
    """Try Open Library first (no API key ever required), then Google Books
    (only if google_books_api_key is set -- see _query_google_books), short-
    circuiting as soon as one provider has a match. A provider that errors
    or times out is skipped rather than failing the whole lookup.
    """
    try:
        result = await _query_open_library(isbn)
    except httpx.HTTPError:
        result = None
    if result is not None:
        return result

    try:
        result = await _query_google_books(isbn, google_books_api_key)
    except httpx.HTTPError:
        result = None
    return result
