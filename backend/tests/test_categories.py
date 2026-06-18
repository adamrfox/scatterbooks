from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal
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


def fts_category_name_for(book_id: int) -> str | None:
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT category_name FROM books_fts WHERE rowid = :id"), {"id": book_id}
        ).first()
        return row[0] if row else None
    finally:
        db.close()


def fts_edition_name_for(book_id: int) -> str | None:
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT edition_name FROM books_fts WHERE rowid = :id"), {"id": book_id}
        ).first()
        return row[0] if row else None
    finally:
        db.close()


def test_create_category_requires_librarian(admin_client):
    reader_client = ensure_reader(admin_client, "cat_reader1")
    try:
        response = reader_client.post("/api/categories", json={"name": "Mystery"})
        assert response.status_code == 403
    finally:
        reader_client.__exit__(None, None, None)


def test_create_list_rename_delete_category(admin_client):
    librarian_client = ensure_librarian(admin_client, "cat_librarian1")
    try:
        create = librarian_client.post("/api/categories", json={"name": "Horror"})
        assert create.status_code == 201
        category_id = create.json()["id"]

        listing = librarian_client.get("/api/categories")
        assert listing.status_code == 200
        assert any(c["name"] == "Horror" for c in listing.json())

        rename = librarian_client.patch(f"/api/categories/{category_id}", json={"name": "Horror/Thriller"})
        assert rename.status_code == 200
        assert rename.json()["name"] == "Horror/Thriller"

        delete = librarian_client.delete(f"/api/categories/{category_id}")
        assert delete.status_code == 204

        missing = librarian_client.patch(f"/api/categories/{category_id}", json={"name": "x"})
        assert missing.status_code == 404
    finally:
        librarian_client.__exit__(None, None, None)


def test_create_category_rejects_case_insensitive_duplicate(admin_client):
    librarian_client = ensure_librarian(admin_client, "cat_librarian2")
    try:
        first = librarian_client.post("/api/categories", json={"name": "Biography"})
        assert first.status_code == 201

        dupe = librarian_client.post("/api/categories", json={"name": "biography"})
        assert dupe.status_code == 409
    finally:
        librarian_client.__exit__(None, None, None)


def test_delete_category_in_use_is_rejected(admin_client):
    librarian_client = ensure_librarian(admin_client, "cat_librarian3")
    try:
        category = librarian_client.post("/api/categories", json={"name": "Poetry"}).json()
        librarian_client.post(
            "/api/books",
            json={"title": "Leaves of Grass", "author": "Walt Whitman", "category_id": category["id"]},
        )

        delete = librarian_client.delete(f"/api/categories/{category['id']}")
        assert delete.status_code == 409
    finally:
        librarian_client.__exit__(None, None, None)


def test_rename_category_resyncs_fts_index(admin_client):
    librarian_client = ensure_librarian(admin_client, "cat_librarian4")
    try:
        category = librarian_client.post("/api/categories", json={"name": "Classics"}).json()
        book = librarian_client.post(
            "/api/books",
            json={"title": "Moby Dick", "author": "Herman Melville", "category_id": category["id"]},
        ).json()

        assert fts_category_name_for(book["id"]) == "Classics"

        rename = librarian_client.patch(
            f"/api/categories/{category['id']}", json={"name": "Classic Literature"}
        )
        assert rename.status_code == 200

        assert fts_category_name_for(book["id"]) == "Classic Literature"
    finally:
        librarian_client.__exit__(None, None, None)


def test_create_list_rename_delete_edition(admin_client):
    librarian_client = ensure_librarian(admin_client, "ed_librarian1")
    try:
        create = librarian_client.post("/api/editions", json={"name": "Hardcover"})
        assert create.status_code == 201
        edition_id = create.json()["id"]

        listing = librarian_client.get("/api/editions")
        assert listing.status_code == 200
        assert any(e["name"] == "Hardcover" for e in listing.json())

        rename = librarian_client.patch(f"/api/editions/{edition_id}", json={"name": "Hardback"})
        assert rename.status_code == 200
        assert rename.json()["name"] == "Hardback"

        delete = librarian_client.delete(f"/api/editions/{edition_id}")
        assert delete.status_code == 204
    finally:
        librarian_client.__exit__(None, None, None)


def test_delete_edition_in_use_is_rejected_and_fts_resyncs_on_rename(admin_client):
    librarian_client = ensure_librarian(admin_client, "ed_librarian2")
    try:
        edition = librarian_client.post("/api/editions", json={"name": "1st Edition"}).json()
        book = librarian_client.post(
            "/api/books",
            json={"title": "Dracula", "author": "Bram Stoker", "edition_id": edition["id"]},
        ).json()

        delete = librarian_client.delete(f"/api/editions/{edition['id']}")
        assert delete.status_code == 409

        rename = librarian_client.patch(
            f"/api/editions/{edition['id']}", json={"name": "First Edition"}
        )
        assert rename.status_code == 200
        assert fts_edition_name_for(book["id"]) == "First Edition"
    finally:
        librarian_client.__exit__(None, None, None)


def fts_match_rowids(query: str) -> set[int]:
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT rowid FROM books_fts WHERE books_fts MATCH :q"), {"q": query}
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        db.close()


def test_fts_index_tracks_book_insert_update_delete(admin_client):
    librarian_client = ensure_librarian(admin_client, "fts_librarian1")
    try:
        book = librarian_client.post(
            "/api/books", json={"title": "Foundation", "author": "Isaac Asimov"}
        ).json()
        assert book["id"] in fts_match_rowids("title:Foundation")
        assert book["id"] in fts_match_rowids("author:Asimov")

        librarian_client.patch(f"/api/books/{book['id']}", json={"title": "Caves of Steel"})
        assert book["id"] not in fts_match_rowids("title:Foundation")
        assert book["id"] in fts_match_rowids("title:Caves")

        librarian_client.delete(f"/api/books/{book['id']}")
        assert book["id"] not in fts_match_rowids("title:Caves")
    finally:
        librarian_client.__exit__(None, None, None)
