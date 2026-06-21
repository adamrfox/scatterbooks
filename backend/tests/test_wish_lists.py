import io

from fastapi.testclient import TestClient
from PIL import Image

from app.images import wish_list_entry_full_image_path
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


def make_image_bytes(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def make_wish_list(client: TestClient, name: str, is_public: bool = False) -> dict:
    response = client.post("/api/wish-lists", json={"name": name, "is_public": is_public})
    assert response.status_code == 201, response.text
    return response.json()


def make_entry(client: TestClient, wish_list_id: int, title: str = "Dune") -> dict:
    response = client.post(
        f"/api/wish-lists/{wish_list_id}/entries",
        json={"title": title, "author": "Frank Herbert"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_wish_list_requires_librarian(admin_client):
    reader_client = ensure_reader(admin_client, "wl_reader_create")
    try:
        response = reader_client.post("/api/wish-lists", json={"name": "Nope"})
        assert response.status_code == 403
    finally:
        reader_client.__exit__(None, None, None)


def test_owner_can_manage_list_and_entries(admin_client):
    librarian_client = ensure_librarian(admin_client, "wl_owner1")
    try:
        wish_list = make_wish_list(librarian_client, "My Wish List")
        assert wish_list["is_public"] is False
        assert wish_list["entry_count"] == 0
        assert wish_list["owner_username"] == "wl_owner1"

        entry = make_entry(librarian_client, wish_list["id"], "Dune")
        assert entry["title"] == "Dune"
        assert entry["cover_image_id"] is None

        listed = librarian_client.get(f"/api/wish-lists/{wish_list['id']}/entries")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        updated = librarian_client.patch(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}",
            json={"notes": "Read this next"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["notes"] == "Read this next"

        renamed = librarian_client.patch(
            f"/api/wish-lists/{wish_list['id']}", json={"name": "Renamed List"}
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Renamed List"

        upload = librarian_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/images",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert upload.status_code == 201, upload.text

        with_cover = librarian_client.get(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}"
        )
        assert with_cover.json()["cover_image_id"] == upload.json()["id"]

        deleted_entry = librarian_client.delete(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}"
        )
        assert deleted_entry.status_code == 204

        missing = librarian_client.get(f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}")
        assert missing.status_code == 404
    finally:
        librarian_client.__exit__(None, None, None)


def test_private_list_visible_only_to_owner_and_admin(admin_client):
    owner_client = ensure_librarian(admin_client, "wl_private_owner")
    other_client = ensure_librarian(admin_client, "wl_private_other")
    try:
        wish_list = make_wish_list(owner_client, "Private List")

        owner_view = owner_client.get(f"/api/wish-lists/{wish_list['id']}")
        assert owner_view.status_code == 200

        other_view = other_client.get(f"/api/wish-lists/{wish_list['id']}")
        assert other_view.status_code == 404

        admin_view = admin_client.get(f"/api/wish-lists/{wish_list['id']}")
        assert admin_view.status_code == 200

        other_list_view = other_client.get("/api/wish-lists")
        assert wish_list["id"] not in [w["id"] for w in other_list_view.json()]

        admin_list_view = admin_client.get("/api/wish-lists")
        assert wish_list["id"] in [w["id"] for w in admin_list_view.json()]
    finally:
        owner_client.__exit__(None, None, None)
        other_client.__exit__(None, None, None)


def test_public_list_visible_to_any_authenticated_user(admin_client):
    owner_client = ensure_librarian(admin_client, "wl_public_owner")
    reader_client = ensure_reader(admin_client, "wl_public_reader")
    try:
        wish_list = make_wish_list(owner_client, "Public List", is_public=True)

        reader_view = reader_client.get(f"/api/wish-lists/{wish_list['id']}")
        assert reader_view.status_code == 200

        reader_list_view = reader_client.get("/api/wish-lists")
        assert wish_list["id"] in [w["id"] for w in reader_list_view.json()]
    finally:
        owner_client.__exit__(None, None, None)
        reader_client.__exit__(None, None, None)


def test_non_owner_forbidden_to_mutate_public_list(admin_client):
    owner_client = ensure_librarian(admin_client, "wl_mutate_owner")
    other_client = ensure_librarian(admin_client, "wl_mutate_other")
    try:
        wish_list = make_wish_list(owner_client, "Editable Only By Owner", is_public=True)
        entry = make_entry(owner_client, wish_list["id"])

        # Visible (public), but not owned -- mutation attempts must be 403,
        # not 404 (the list's existence is already known to this caller).
        forbidden_rename = other_client.patch(
            f"/api/wish-lists/{wish_list['id']}", json={"name": "Hijacked"}
        )
        assert forbidden_rename.status_code == 403

        forbidden_entry_create = other_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries",
            json={"title": "Intruder", "author": "Someone"},
        )
        assert forbidden_entry_create.status_code == 403

        forbidden_entry_update = other_client.patch(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}", json={"notes": "nope"}
        )
        assert forbidden_entry_update.status_code == 403

        forbidden_image = other_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/images",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert forbidden_image.status_code == 403

        forbidden_move = other_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/move-to-library"
        )
        assert forbidden_move.status_code == 403

        forbidden_delete = other_client.delete(f"/api/wish-lists/{wish_list['id']}")
        assert forbidden_delete.status_code == 403

        # Admin can do all the same things despite not owning the list.
        admin_rename = admin_client.patch(
            f"/api/wish-lists/{wish_list['id']}", json={"name": "Admin Renamed"}
        )
        assert admin_rename.status_code == 200, admin_rename.text
    finally:
        owner_client.__exit__(None, None, None)
        other_client.__exit__(None, None, None)


def test_move_entry_to_library_creates_book_with_photo_and_removes_entry(admin_client):
    librarian_client = ensure_librarian(admin_client, "wl_move_owner")
    try:
        wish_list = make_wish_list(librarian_client, "Move Test List")
        entry = make_entry(librarian_client, wish_list["id"], "Foundation")
        librarian_client.patch(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}",
            json={"year": 1951, "notes": "Asimov classic"},
        )
        image_bytes = make_image_bytes(color=(99, 88, 77))
        upload = librarian_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/images",
            files={"file": ("cover.jpg", image_bytes, "image/jpeg")},
        )
        assert upload.status_code == 201, upload.text

        # The upload pipeline re-encodes the JPEG (process_upload), so the
        # entry's *stored* bytes -- not the raw bytes we uploaded -- are
        # what the moved book's copy should match byte-for-byte.
        entry_image_bytes = librarian_client.get(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/images/{upload.json()['id']}"
        ).content

        move = librarian_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/move-to-library"
        )
        assert move.status_code == 201, move.text
        book = move.json()
        assert book["title"] == "Foundation"
        assert book["author"] == "Frank Herbert"
        assert book["year"] == 1951
        assert book["notes"] == "Asimov classic"
        assert book["cover_image_id"] is not None

        # The new book's photo is a real, independent file under the books
        # image directory with the same bytes as the entry's stored photo.
        full_image = librarian_client.get(f"/api/books/{book['id']}/images/{book['cover_image_id']}")
        assert full_image.status_code == 200
        assert full_image.content == entry_image_bytes

        # The entry is gone, but the wish list itself still exists.
        gone = librarian_client.get(f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}")
        assert gone.status_code == 404
        still_there = librarian_client.get(f"/api/wish-lists/{wish_list['id']}")
        assert still_there.status_code == 200

        # The wish-list-side image file was cleaned up.
        assert not wish_list_entry_full_image_path(entry["id"], upload.json()["id"]).exists()
    finally:
        librarian_client.__exit__(None, None, None)


def test_deleting_wish_list_cascades_to_entries_and_image_files(admin_client):
    librarian_client = ensure_librarian(admin_client, "wl_cascade_owner")
    try:
        wish_list = make_wish_list(librarian_client, "Cascade Test List")
        entry = make_entry(librarian_client, wish_list["id"])
        upload = librarian_client.post(
            f"/api/wish-lists/{wish_list['id']}/entries/{entry['id']}/images",
            files={"file": ("cover.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert upload.status_code == 201, upload.text
        image_path = wish_list_entry_full_image_path(entry["id"], upload.json()["id"])
        assert image_path.exists()

        deleted = librarian_client.delete(f"/api/wish-lists/{wish_list['id']}")
        assert deleted.status_code == 204

        assert librarian_client.get(f"/api/wish-lists/{wish_list['id']}").status_code == 404
        assert not image_path.exists()
    finally:
        librarian_client.__exit__(None, None, None)
