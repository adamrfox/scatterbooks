from fastapi.testclient import TestClient

from app.main import app


def login_as(username: str, password: str) -> TestClient:
    client = TestClient(app)
    client.__enter__()
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client


def test_create_user_requires_admin(admin_client):
    create = admin_client.post(
        "/api/users", json={"username": "librarian1", "password": "librarianpw1", "role": "librarian"}
    )
    assert create.status_code == 201
    librarian = create.json()
    assert librarian["role"] == "librarian"

    librarian_client = login_as("librarian1", "librarianpw1")
    try:
        forbidden = librarian_client.post(
            "/api/users", json={"username": "nope", "password": "whatever1", "role": "user"}
        )
        assert forbidden.status_code == 403
    finally:
        librarian_client.__exit__(None, None, None)


def test_create_user_rejects_invalid_role(admin_client):
    response = admin_client.post(
        "/api/users", json={"username": "bogus", "password": "password123", "role": "superadmin"}
    )
    assert response.status_code == 422


def test_create_user_rejects_duplicate_username(admin_client):
    admin_client.post(
        "/api/users", json={"username": "dupe", "password": "password123", "role": "user"}
    )
    response = admin_client.post(
        "/api/users", json={"username": "dupe", "password": "password123", "role": "user"}
    )
    assert response.status_code == 409


def test_admin_can_list_update_and_deactivate_user(admin_client):
    create = admin_client.post(
        "/api/users", json={"username": "regular1", "password": "regularpw1", "role": "user"}
    )
    user_id = create.json()["id"]

    listing = admin_client.get("/api/users")
    assert listing.status_code == 200
    assert any(u["username"] == "regular1" for u in listing.json())

    update = admin_client.patch(f"/api/users/{user_id}", json={"role": "librarian"})
    assert update.status_code == 200
    assert update.json()["role"] == "librarian"

    deactivate = admin_client.delete(f"/api/users/{user_id}")
    assert deactivate.status_code == 204

    user_client = TestClient(app)
    with user_client:
        login = user_client.post(
            "/api/auth/login", json={"username": "regular1", "password": "regularpw1"}
        )
        assert login.status_code == 401


def test_admin_cannot_deactivate_self(admin_client):
    me = admin_client.get("/api/auth/me").json()
    response = admin_client.delete(f"/api/users/{me['id']}")
    assert response.status_code == 400


def test_self_password_change(admin_client):
    create = admin_client.post(
        "/api/users", json={"username": "selfchange1", "password": "originalpw1", "role": "user"}
    )
    assert create.status_code == 201

    user_client = login_as("selfchange1", "originalpw1")
    try:
        wrong_current = user_client.post(
            "/api/users/me/password",
            json={"current_password": "notit", "new_password": "newpassword1"},
        )
        assert wrong_current.status_code == 400

        change = user_client.post(
            "/api/users/me/password",
            json={"current_password": "originalpw1", "new_password": "newpassword1"},
        )
        assert change.status_code == 204
    finally:
        user_client.__exit__(None, None, None)

    relogin_client = TestClient(app)
    with relogin_client:
        old_login = relogin_client.post(
            "/api/auth/login", json={"username": "selfchange1", "password": "originalpw1"}
        )
        assert old_login.status_code == 401

        new_login = relogin_client.post(
            "/api/auth/login", json={"username": "selfchange1", "password": "newpassword1"}
        )
        assert new_login.status_code == 200
