import os
import tempfile

_tmp_data_dir = tempfile.mkdtemp(prefix="scatterbooks-test-")
os.environ["DATA_DIR"] = _tmp_data_dir
os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
os.environ["INITIAL_ADMIN_PASSWORD"] = "admin-password-123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-password-123"


@pytest.fixture(scope="session")
def admin_client():
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        yield test_client


@pytest.fixture
def anon_client():
    with TestClient(app) as test_client:
        yield test_client
