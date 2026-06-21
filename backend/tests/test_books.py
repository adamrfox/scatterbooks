from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Category, Edition


def login_as(username: str, password: str) -> TestClient:
    client = TestClient(app)
    client.__enter__()
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client


def make_category(name: str) -> int:
    db = SessionLocal()
    try:
        category = Category(name=name)
        db.add(category)
        db.commit()
        db.refresh(category)
        return category.id
    finally:
        db.close()


def make_edition(name: str) -> int:
    db = SessionLocal()
    try:
        edition = Edition(name=name)
        db.add(edition)
        db.commit()
        db.refresh(edition)
        return edition.id
    finally:
        db.close()


def ensure_librarian(admin_client) -> TestClient:
    admin_client.post(
        "/api/users",
        json={"username": "books_librarian", "password": "librarianpw1", "role": "librarian"},
    )
    return login_as("books_librarian", "librarianpw1")


def ensure_reader(admin_client) -> TestClient:
    admin_client.post(
        "/api/users", json={"username": "books_reader", "password": "readerpw1", "role": "user"}
    )
    return login_as("books_reader", "readerpw1")


def test_create_book_requires_librarian(admin_client):
    reader_client = ensure_reader(admin_client)
    try:
        response = reader_client.post(
            "/api/books", json={"title": "The Hobbit", "author": "J.R.R. Tolkien"}
        )
        assert response.status_code == 403
    finally:
        reader_client.__exit__(None, None, None)


def test_create_get_update_delete_book(admin_client):
    librarian_client = ensure_librarian(admin_client)
    try:
        category_id = make_category("Fantasy")
        edition_id = make_edition("Paperback")

        create = librarian_client.post(
            "/api/books",
            json={
                "title": "The Fellowship of the Ring",
                "author": "J.R.R. Tolkien",
                "category_id": category_id,
                "edition_id": edition_id,
                "notes": "First book in the trilogy",
                "year": 1954,
            },
        )
        assert create.status_code == 201, create.text
        book = create.json()
        assert book["title"] == "The Fellowship of the Ring"
        assert book["category"]["name"] == "Fantasy"
        assert book["edition"]["name"] == "Paperback"
        assert book["year"] == 1954
        book_id = book["id"]

        fetched = librarian_client.get(f"/api/books/{book_id}")
        assert fetched.status_code == 200
        assert fetched.json()["author"] == "J.R.R. Tolkien"

        updated = librarian_client.patch(f"/api/books/{book_id}", json={"notes": "Updated notes"})
        assert updated.status_code == 200
        assert updated.json()["notes"] == "Updated notes"
        assert updated.json()["title"] == "The Fellowship of the Ring"

        cleared = librarian_client.patch(f"/api/books/{book_id}", json={"category_id": None})
        assert cleared.status_code == 200
        assert cleared.json()["category_id"] is None
        assert cleared.json()["category"] is None

        deleted = librarian_client.delete(f"/api/books/{book_id}")
        assert deleted.status_code == 204

        missing = librarian_client.get(f"/api/books/{book_id}")
        assert missing.status_code == 404
    finally:
        librarian_client.__exit__(None, None, None)


def test_year_is_optional_and_clearable(admin_client):
    librarian_client = ensure_librarian(admin_client)
    try:
        create = librarian_client.post(
            "/api/books", json={"title": "No Year Given", "author": "Author"}
        )
        assert create.status_code == 201, create.text
        assert create.json()["year"] is None
        book_id = create.json()["id"]

        set_year = librarian_client.patch(f"/api/books/{book_id}", json={"year": 1999})
        assert set_year.status_code == 200, set_year.text
        assert set_year.json()["year"] == 1999

        cleared = librarian_client.patch(f"/api/books/{book_id}", json={"year": None})
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["year"] is None
    finally:
        librarian_client.__exit__(None, None, None)


def test_create_book_requires_title_and_author(admin_client):
    librarian_client = ensure_librarian(admin_client)
    try:
        response = librarian_client.post("/api/books", json={"title": "Missing Author"})
        assert response.status_code == 422
    finally:
        librarian_client.__exit__(None, None, None)


def test_create_book_rejects_unknown_category(admin_client):
    librarian_client = ensure_librarian(admin_client)
    try:
        response = librarian_client.post(
            "/api/books", json={"title": "T", "author": "A", "category_id": 999999}
        )
        assert response.status_code == 400
    finally:
        librarian_client.__exit__(None, None, None)


def test_list_books_filters_by_category(admin_client):
    librarian_client = ensure_librarian(admin_client)
    try:
        category_id = make_category("Sci-Fi Filter Test")
        librarian_client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category_id": category_id},
        )
        librarian_client.post("/api/books", json={"title": "Unrelated Book", "author": "Someone"})

        filtered = librarian_client.get("/api/books", params={"category_id": category_id})
        assert filtered.status_code == 200
        titles = [b["title"] for b in filtered.json()]
        assert titles == ["Dune"]
    finally:
        librarian_client.__exit__(None, None, None)


def test_reader_can_list_and_get_but_not_mutate(admin_client):
    librarian_client = ensure_librarian(admin_client)
    reader_client = ensure_reader(admin_client)
    try:
        create = librarian_client.post(
            "/api/books", json={"title": "Reader Visible Book", "author": "Author"}
        )
        book_id = create.json()["id"]

        listing = reader_client.get("/api/books")
        assert listing.status_code == 200

        detail = reader_client.get(f"/api/books/{book_id}")
        assert detail.status_code == 200

        forbidden_update = reader_client.patch(f"/api/books/{book_id}", json={"notes": "nope"})
        assert forbidden_update.status_code == 403

        forbidden_delete = reader_client.delete(f"/api/books/{book_id}")
        assert forbidden_delete.status_code == 403
    finally:
        librarian_client.__exit__(None, None, None)
        reader_client.__exit__(None, None, None)


def test_cover_image_id_reflects_lowest_position_image(admin_client):
    librarian_client = ensure_librarian(admin_client)
    try:
        import io

        from PIL import Image

        def make_image_bytes() -> bytes:
            buffer = io.BytesIO()
            Image.new("RGB", (20, 20), (5, 5, 5)).save(buffer, format="JPEG")
            return buffer.getvalue()

        book = librarian_client.post(
            "/api/books", json={"title": "Cover Image Test", "author": "Author"}
        ).json()
        assert book["cover_image_id"] is None

        first = librarian_client.post(
            f"/api/books/{book['id']}/images",
            files={"file": ("a.jpg", make_image_bytes(), "image/jpeg")},
        ).json()
        second = librarian_client.post(
            f"/api/books/{book['id']}/images",
            files={"file": ("b.jpg", make_image_bytes(), "image/jpeg")},
        ).json()

        fetched = librarian_client.get(f"/api/books/{book['id']}").json()
        assert fetched["cover_image_id"] == first["id"]

        librarian_client.delete(f"/api/books/{book['id']}/images/{first['id']}")
        fetched_after_delete = librarian_client.get(f"/api/books/{book['id']}").json()
        assert fetched_after_delete["cover_image_id"] == second["id"]
    finally:
        librarian_client.__exit__(None, None, None)
