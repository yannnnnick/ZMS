from __future__ import annotations

import os
import sys
from collections.abc import Callable, Generator
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "test-secret-for-zms-cookie-auth-suite-32-bytes")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import create_app
from app.seed import seed_demo_data
from app.security import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    seed_demo_data(TestingSessionLocal)

    app = create_app(seed=False, init_database=False)
    app.state.testing_session_factory = TestingSessionLocal

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def login(client: TestClient) -> Callable[[str, str], dict[str, str]]:
    """Return a helper that logs the shared client in and yields CSRF headers."""

    def _login(email: str, password: str) -> dict[str, str]:
        response = client.post("/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        body = response.json()
        assert "access_token" not in body
        assert client.cookies.get(AUTH_COOKIE_NAME)
        assert client.cookies.get(CSRF_COOKIE_NAME)
        return {"X-CSRF-Token": body["csrf_token"]}

    return _login
