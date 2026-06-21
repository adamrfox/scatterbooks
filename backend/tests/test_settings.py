import httpx
from fastapi.testclient import TestClient

from app.config import settings as env_settings
from app.main import app


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


def reset_settings(admin_client, monkeypatch):
    """app_settings is a true singleton shared across the whole test session
    (not per-test-isolated like most resources in this suite) -- reset both
    keys and env fallbacks explicitly rather than assuming a pristine state.
    """
    monkeypatch.setattr(env_settings, "google_books_api_key", None)
    monkeypatch.setattr(env_settings, "anthropic_api_key", None)
    admin_client.patch(
        "/api/settings", json={"google_books_api_key": None, "anthropic_api_key": None}
    )


def test_admin_can_get_and_set_google_books_key(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)

    initial = admin_client.get("/api/settings")
    assert initial.status_code == 200, initial.text
    assert initial.json()["google_books_api_key_configured"] is False
    assert initial.json()["google_books_api_key_source"] == "none"

    update = admin_client.patch("/api/settings", json={"google_books_api_key": "my-real-key"})
    assert update.status_code == 200, update.text
    assert update.json()["google_books_api_key_configured"] is True
    assert update.json()["google_books_api_key_source"] == "database"

    confirm = admin_client.get("/api/settings")
    assert confirm.json()["google_books_api_key_source"] == "database"


def test_admin_can_get_and_set_anthropic_key(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)

    initial = admin_client.get("/api/settings")
    assert initial.json()["anthropic_api_key_configured"] is False
    assert initial.json()["anthropic_api_key_source"] == "none"

    update = admin_client.patch("/api/settings", json={"anthropic_api_key": "my-claude-key"})
    assert update.status_code == 200, update.text
    assert update.json()["anthropic_api_key_configured"] is True
    assert update.json()["anthropic_api_key_source"] == "database"


def test_patching_one_key_does_not_clear_the_other(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)

    admin_client.patch("/api/settings", json={"google_books_api_key": "google-key"})
    admin_client.patch("/api/settings", json={"anthropic_api_key": "claude-key"})

    result = admin_client.get("/api/settings").json()
    assert result["google_books_api_key_configured"] is True
    assert result["anthropic_api_key_configured"] is True

    # Updating only one field must leave the other untouched, not implicitly
    # clear it (the bug this endpoint had before exclude_unset was added).
    admin_client.patch("/api/settings", json={"google_books_api_key": "google-key-2"})
    after = admin_client.get("/api/settings").json()
    assert after["anthropic_api_key_configured"] is True


def test_clearing_key_reverts_to_none_without_env_fallback(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)

    admin_client.patch("/api/settings", json={"google_books_api_key": "some-key"})
    cleared = admin_client.patch("/api/settings", json={"google_books_api_key": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["google_books_api_key_configured"] is False
    assert cleared.json()["google_books_api_key_source"] == "none"


def test_clearing_key_falls_back_to_env_var(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)
    monkeypatch.setattr(env_settings, "google_books_api_key", "env-fallback-key")

    admin_client.patch("/api/settings", json={"google_books_api_key": "db-key"})
    cleared = admin_client.patch("/api/settings", json={"google_books_api_key": ""})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["google_books_api_key_configured"] is True
    assert cleared.json()["google_books_api_key_source"] == "environment"


def test_non_admin_forbidden(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)

    librarian_client = ensure_librarian(admin_client, "settings_librarian1")
    reader_client = ensure_reader(admin_client, "settings_reader1")
    try:
        assert librarian_client.get("/api/settings").status_code == 403
        assert librarian_client.patch("/api/settings", json={"google_books_api_key": "x"}).status_code == 403
        assert librarian_client.patch("/api/settings", json={"anthropic_api_key": "x"}).status_code == 403
        assert reader_client.get("/api/settings").status_code == 403
        assert reader_client.patch("/api/settings", json={"google_books_api_key": "x"}).status_code == 403
    finally:
        librarian_client.__exit__(None, None, None)
        reader_client.__exit__(None, None, None)


class _FakeHttpResponse:
    def __init__(self, status_code: int, json_data: dict) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict:
        return self._json_data


def test_database_key_takes_precedence_in_real_isbn_lookup(admin_client, monkeypatch):
    reset_settings(admin_client, monkeypatch)
    monkeypatch.setattr(env_settings, "google_books_api_key", "env-key-should-not-be-used")
    admin_client.patch("/api/settings", json={"google_books_api_key": "db-key-should-be-used"})

    seen_keys = []

    async def fake_open_library_get(self, url, params=None, **kwargs):
        return _FakeHttpResponse(200, {})  # Open Library miss -> falls through to Google Books

    async def fake_google_books_get(self, url, params=None, **kwargs):
        seen_keys.append(params.get("key"))
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

    async def fake_get(self, url, params=None, **kwargs):
        if "openlibrary.org" in url:
            return await fake_open_library_get(self, url, params, **kwargs)
        return await fake_google_books_get(self, url, params, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    response = admin_client.get("/api/isbn/9780441013593")
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Dune"
    assert seen_keys == ["db-key-should-be-used"]
