import asyncio

import httpx
from fastapi.testclient import TestClient

import app.isbn_lookup as isbn_lookup
from app.main import app
from app.schemas.isbn import IsbnLookupResult


def login_as(username: str, password: str) -> TestClient:
    client = TestClient(app)
    client.__enter__()
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client


def ensure_librarian(admin_client, username: str) -> TestClient:
    admin_client.post(
        "/api/users", json={"username": username, "password": "librarianpw1", "role": "librarian"}
    )
    return login_as(username, "librarianpw1")


def ensure_reader(admin_client, username: str) -> TestClient:
    admin_client.post(
        "/api/users", json={"username": username, "password": "readerpw1", "role": "user"}
    )
    return login_as(username, "readerpw1")


async def _miss(isbn: str) -> IsbnLookupResult | None:
    return None


def test_open_library_hit_returns_title_and_author(admin_client, monkeypatch):
    async def fake_open_library(isbn: str) -> IsbnLookupResult | None:
        return IsbnLookupResult(isbn=isbn, title="Dune", author="Frank Herbert")

    monkeypatch.setattr(isbn_lookup, "_query_open_library", fake_open_library)
    monkeypatch.setattr(isbn_lookup, "_query_google_books", _miss)

    librarian_client = ensure_librarian(admin_client, "isbn_librarian1")
    try:
        response = librarian_client.get("/api/isbn/9780441013593")
        assert response.status_code == 200, response.text
        assert response.json() == {"isbn": "9780441013593", "title": "Dune", "author": "Frank Herbert"}
    finally:
        librarian_client.__exit__(None, None, None)


def test_falls_back_to_google_books_when_open_library_misses(admin_client, monkeypatch):
    async def fake_google_books(isbn: str) -> IsbnLookupResult | None:
        return IsbnLookupResult(isbn=isbn, title="Foundation", author="Isaac Asimov")

    monkeypatch.setattr(isbn_lookup, "_query_open_library", _miss)
    monkeypatch.setattr(isbn_lookup, "_query_google_books", fake_google_books)

    librarian_client = ensure_librarian(admin_client, "isbn_librarian2")
    try:
        response = librarian_client.get("/api/isbn/9780553293357")
        assert response.status_code == 200, response.text
        assert response.json()["title"] == "Foundation"
        assert response.json()["author"] == "Isaac Asimov"
    finally:
        librarian_client.__exit__(None, None, None)


def test_both_providers_miss_returns_404(admin_client, monkeypatch):
    monkeypatch.setattr(isbn_lookup, "_query_open_library", _miss)
    monkeypatch.setattr(isbn_lookup, "_query_google_books", _miss)

    librarian_client = ensure_librarian(admin_client, "isbn_librarian3")
    try:
        response = librarian_client.get("/api/isbn/0000000000000")
        assert response.status_code == 404
    finally:
        librarian_client.__exit__(None, None, None)


def test_reader_role_forbidden(admin_client, monkeypatch):
    monkeypatch.setattr(isbn_lookup, "_query_open_library", _miss)
    monkeypatch.setattr(isbn_lookup, "_query_google_books", _miss)

    reader_client = ensure_reader(admin_client, "isbn_reader1")
    try:
        response = reader_client.get("/api/isbn/9780441013593")
        assert response.status_code == 403
    finally:
        reader_client.__exit__(None, None, None)


def test_isbn_with_hyphens_is_normalized_before_lookup(admin_client, monkeypatch):
    seen_isbns = []

    async def fake_open_library(isbn: str) -> IsbnLookupResult | None:
        seen_isbns.append(isbn)
        return IsbnLookupResult(isbn=isbn, title="Dune", author="Frank Herbert")

    monkeypatch.setattr(isbn_lookup, "_query_open_library", fake_open_library)
    monkeypatch.setattr(isbn_lookup, "_query_google_books", _miss)

    librarian_client = ensure_librarian(admin_client, "isbn_librarian4")
    try:
        response = librarian_client.get("/api/isbn/978-0-441-01359-3")
        assert response.status_code == 200, response.text
        assert seen_isbns == ["9780441013593"]
    finally:
        librarian_client.__exit__(None, None, None)


class _FakeHttpResponse:
    def __init__(self, status_code: int, json_data: dict) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict:
        return self._json_data


def test_google_books_skipped_without_api_key(monkeypatch):
    monkeypatch.setattr(isbn_lookup.settings, "google_books_api_key", None)

    async def fail_if_called(self, *args, **kwargs):
        raise AssertionError("should not make a network call without an API key")

    monkeypatch.setattr(httpx.AsyncClient, "get", fail_if_called)

    result = asyncio.run(isbn_lookup._query_google_books("9780441013593"))
    assert result is None


def test_google_books_rejects_fuzzy_match_with_different_isbn(monkeypatch):
    monkeypatch.setattr(isbn_lookup.settings, "google_books_api_key", "fake-key-for-test")

    async def fake_get(self, url, params=None, **kwargs):
        return _FakeHttpResponse(
            200,
            {
                "items": [
                    {
                        "volumeInfo": {
                            "title": "Unrelated Book",
                            "authors": ["Someone Else"],
                            "industryIdentifiers": [
                                {"type": "ISBN_13", "identifier": "9999999999999"}
                            ],
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(isbn_lookup._query_google_books("0000000000000"))
    assert result is None


def test_google_books_accepts_matching_isbn(monkeypatch):
    monkeypatch.setattr(isbn_lookup.settings, "google_books_api_key", "fake-key-for-test")

    async def fake_get(self, url, params=None, **kwargs):
        return _FakeHttpResponse(
            200,
            {
                "items": [
                    {
                        "volumeInfo": {
                            "title": "Dune",
                            "authors": ["Frank Herbert"],
                            "industryIdentifiers": [
                                {"type": "ISBN_13", "identifier": "9780441013593"}
                            ],
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(isbn_lookup._query_google_books("9780441013593"))
    assert result is not None
    assert result.title == "Dune"
    assert result.author == "Frank Herbert"
