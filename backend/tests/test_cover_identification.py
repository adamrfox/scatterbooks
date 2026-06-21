import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image

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


def make_image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (60, 80), (10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def reset_anthropic_key(admin_client, monkeypatch, value: str | None = None):
    monkeypatch.setattr(env_settings, "anthropic_api_key", None)
    admin_client.patch("/api/settings", json={"anthropic_api_key": value})


class _FakeHttpResponse:
    def __init__(self, status_code: int, json_data: dict) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict:
        return self._json_data


def _claude_response(text: str) -> _FakeHttpResponse:
    return _FakeHttpResponse(200, {"content": [{"type": "text", "text": text}]})


def test_not_configured_returns_400(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, None)

    librarian_client = ensure_librarian(admin_client, "cover_librarian1")
    try:
        response = librarian_client.post(
            "/api/identify-cover",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 400, response.text
    finally:
        librarian_client.__exit__(None, None, None)


def test_successful_identification(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, "fake-claude-key")

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        return _claude_response('{"title": "Dune", "author": "Frank Herbert"}')

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    librarian_client = ensure_librarian(admin_client, "cover_librarian2")
    try:
        response = librarian_client.post(
            "/api/identify-cover",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"title": "Dune", "author": "Frank Herbert"}
    finally:
        librarian_client.__exit__(None, None, None)


def test_unidentifiable_cover_returns_null_fields(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, "fake-claude-key")

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        return _claude_response('{"title": null, "author": null}')

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    librarian_client = ensure_librarian(admin_client, "cover_librarian3")
    try:
        response = librarian_client.post(
            "/api/identify-cover",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"title": None, "author": None}
    finally:
        librarian_client.__exit__(None, None, None)


def test_malformed_model_reply_returns_502(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, "fake-claude-key")

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        return _claude_response("I think this might be Dune but I'm not sure!")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    librarian_client = ensure_librarian(admin_client, "cover_librarian4")
    try:
        response = librarian_client.post(
            "/api/identify-cover",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 502, response.text
    finally:
        librarian_client.__exit__(None, None, None)


def test_markdown_fenced_json_is_parsed(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, "fake-claude-key")

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        return _claude_response('```json\n{"title": "Dune", "author": "Frank Herbert"}\n```')

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    librarian_client = ensure_librarian(admin_client, "cover_librarian5")
    try:
        response = librarian_client.post(
            "/api/identify-cover",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"title": "Dune", "author": "Frank Herbert"}
    finally:
        librarian_client.__exit__(None, None, None)


def test_reader_role_forbidden(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, "fake-claude-key")

    reader_client = ensure_reader(admin_client, "cover_reader1")
    try:
        response = reader_client.post(
            "/api/identify-cover",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 403
    finally:
        reader_client.__exit__(None, None, None)


def test_invalid_image_returns_400(admin_client, monkeypatch):
    reset_anthropic_key(admin_client, monkeypatch, "fake-claude-key")

    librarian_client = ensure_librarian(admin_client, "cover_librarian6")
    try:
        response = librarian_client.post(
            "/api/identify-cover",
            files={"file": ("not_an_image.jpg", b"this is not an image", "image/jpeg")},
        )
        assert response.status_code == 400
    finally:
        librarian_client.__exit__(None, None, None)
