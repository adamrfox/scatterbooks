import io
import os

from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
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


def make_image_bytes(
    size: tuple[int, int] = (60, 40),
    color: tuple[int, int, int] = (200, 50, 50),
    fmt: str = "JPEG",
    orientation: int | None = None,
) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    if orientation is not None:
        exif = image.getexif()
        exif[0x0112] = orientation
        image.save(buffer, format=fmt, exif=exif.tobytes())
    else:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


def make_book(client: TestClient, title: str) -> int:
    return client.post("/api/books", json={"title": title, "author": "Author"}).json()["id"]


def test_upload_requires_librarian(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian1")
    reader_client = ensure_reader(admin_client, "img_reader1")
    try:
        book_id = make_book(librarian_client, "Upload Auth Test")
        response = reader_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("photo.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 403
    finally:
        librarian_client.__exit__(None, None, None)
        reader_client.__exit__(None, None, None)


def test_upload_get_and_list_image(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian2")
    try:
        book_id = make_book(librarian_client, "Image Lifecycle Test")

        upload = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("photo.jpg", make_image_bytes(size=(60, 40)), "image/jpeg")},
        )
        assert upload.status_code == 201, upload.text
        image = upload.json()
        assert image["position"] == 0
        assert image["width"] == 60
        assert image["height"] == 40
        assert image["content_type"] == "image/jpeg"

        listing = librarian_client.get(f"/api/books/{book_id}/images")
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        full = librarian_client.get(f"/api/books/{book_id}/images/{image['id']}")
        assert full.status_code == 200
        assert full.headers["content-type"] == "image/jpeg"
        assert len(full.content) > 0

        thumb = librarian_client.get(f"/api/books/{book_id}/images/{image['id']}/thumb")
        assert thumb.status_code == 200
        thumb_image = Image.open(io.BytesIO(thumb.content))
        assert thumb_image.width <= 400
        assert thumb_image.height <= 400
    finally:
        librarian_client.__exit__(None, None, None)


def test_exif_orientation_is_corrected(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian3")
    try:
        book_id = make_book(librarian_client, "EXIF Test")

        raw = make_image_bytes(size=(60, 40), orientation=6)
        upload = librarian_client.post(
            f"/api/books/{book_id}/images", files={"file": ("photo.jpg", raw, "image/jpeg")}
        )
        assert upload.status_code == 201, upload.text
        image = upload.json()
        assert (image["width"], image["height"]) == (40, 60)

        full = librarian_client.get(f"/api/books/{book_id}/images/{image['id']}")
        stored = Image.open(io.BytesIO(full.content))
        assert stored.size == (40, 60)
        assert stored.getexif().get(0x0112) is None
    finally:
        librarian_client.__exit__(None, None, None)


def test_rejects_invalid_image_bytes(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian4")
    try:
        book_id = make_book(librarian_client, "Invalid Upload Test")
        response = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("not_an_image.jpg", b"this is not an image", "image/jpeg")},
        )
        assert response.status_code == 400
    finally:
        librarian_client.__exit__(None, None, None)


def test_rejects_oversized_upload(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian5")
    try:
        book_id = make_book(librarian_client, "Oversized Upload Test")
        oversized = os.urandom((settings.max_upload_mb * 1024 * 1024) + 1)
        response = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("huge.jpg", oversized, "image/jpeg")},
        )
        assert response.status_code == 400
    finally:
        librarian_client.__exit__(None, None, None)


def test_sixth_image_rejected(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian6")
    try:
        book_id = make_book(librarian_client, "Five Image Limit Test")
        for _ in range(5):
            response = librarian_client.post(
                f"/api/books/{book_id}/images",
                files={"file": ("photo.jpg", make_image_bytes(), "image/jpeg")},
            )
            assert response.status_code == 201

        sixth = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("photo.jpg", make_image_bytes(), "image/jpeg")},
        )
        assert sixth.status_code == 409
    finally:
        librarian_client.__exit__(None, None, None)


def test_reorder_swaps_positions(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian7")
    try:
        book_id = make_book(librarian_client, "Reorder Test")
        first = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("a.jpg", make_image_bytes(color=(10, 10, 10)), "image/jpeg")},
        ).json()
        second = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("b.jpg", make_image_bytes(color=(20, 20, 20)), "image/jpeg")},
        ).json()
        assert first["position"] == 0
        assert second["position"] == 1

        reorder = librarian_client.patch(
            f"/api/books/{book_id}/images/{first['id']}", json={"position": 1}
        )
        assert reorder.status_code == 200
        assert reorder.json()["position"] == 1

        listing = librarian_client.get(f"/api/books/{book_id}/images").json()
        positions = {item["id"]: item["position"] for item in listing}
        assert positions[first["id"]] == 1
        assert positions[second["id"]] == 0
    finally:
        librarian_client.__exit__(None, None, None)


def test_delete_image_removes_file_and_frees_position(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian8")
    try:
        book_id = make_book(librarian_client, "Delete Image Test")
        image = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("a.jpg", make_image_bytes(), "image/jpeg")},
        ).json()

        from app.images import full_image_path

        path = full_image_path(book_id, image["id"])
        assert path.exists()

        delete = librarian_client.delete(f"/api/books/{book_id}/images/{image['id']}")
        assert delete.status_code == 204
        assert not path.exists()

        listing = librarian_client.get(f"/api/books/{book_id}/images").json()
        assert listing == []

        replacement = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("b.jpg", make_image_bytes(), "image/jpeg")},
        ).json()
        assert replacement["position"] == 0
    finally:
        librarian_client.__exit__(None, None, None)


def test_deleting_book_removes_image_files(admin_client):
    librarian_client = ensure_librarian(admin_client, "img_librarian9")
    try:
        book_id = make_book(librarian_client, "Book Delete Cascades Images")
        image = librarian_client.post(
            f"/api/books/{book_id}/images",
            files={"file": ("a.jpg", make_image_bytes(), "image/jpeg")},
        ).json()

        from app.images import book_image_dir, full_image_path

        path = full_image_path(book_id, image["id"])
        assert path.exists()

        delete = librarian_client.delete(f"/api/books/{book_id}")
        assert delete.status_code == 204

        assert not path.exists()
        assert not book_image_dir(book_id).exists()
    finally:
        librarian_client.__exit__(None, None, None)
