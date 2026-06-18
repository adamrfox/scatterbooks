from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def test_me_requires_auth(anon_client):
    response = anon_client.get("/api/auth/me")
    assert response.status_code == 401


def test_login_wrong_password_rejected(anon_client):
    response = anon_client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_and_me(anon_client):
    login = anon_client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"

    me = anon_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == ADMIN_USERNAME


def test_logout_invalidates_session(anon_client):
    anon_client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert anon_client.get("/api/auth/me").status_code == 200

    logout = anon_client.post("/api/auth/logout")
    assert logout.status_code == 204

    assert anon_client.get("/api/auth/me").status_code == 401
