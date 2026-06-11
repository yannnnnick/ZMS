from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import create_app
from app.models import User, UserRole
from app.seed import seed_demo_data
from app.security import hash_password


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


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_and_dashboard(client: TestClient) -> None:
    headers = login(client, "admin@example.test", "Admin123!")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["animals_total"] >= 5
    assert body["open_tasks"] >= 1


def test_login_rejects_wrong_password(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@example.test", "password": "Wrong123!"})
    assert response.status_code == 401


def test_login_rejects_overlong_bcrypt_password_without_server_error(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@example.test", "password": "A" * 73})
    assert response.status_code == 401


def test_login_rejects_inactive_user(client: TestClient) -> None:
    session_factory = client.app.state.testing_session_factory
    db = session_factory()
    try:
        db.add(
            User(
                email="inactive@example.test",
                display_name="Inactive Demo",
                role=UserRole.viewer,
                password_hash=hash_password("Inactive123!"),
                is_active=False,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post("/auth/login", json={"email": "inactive@example.test", "password": "Inactive123!"})
    assert response.status_code == 403


def test_viewer_cannot_create_animal(client: TestClient) -> None:
    viewer_headers = login(client, "viewer@example.test", "Viewer123!")
    response = client.post(
        "/animals",
        headers=viewer_headers,
        json={"name": "Testtier", "species_id": 1, "enclosure_id": 1, "sex": "unknown", "health_status": "healthy"},
    )
    assert response.status_code == 403


def test_keeper_can_create_animal_and_audit_is_written(client: TestClient) -> None:
    keeper_headers = login(client, "keeper@example.test", "Keeper123!")
    response = client.post(
        "/animals",
        headers=keeper_headers,
        json={"name": "Nala", "species_id": 3, "enclosure_id": 3, "sex": "female", "health_status": "healthy"},
    )
    assert response.status_code == 201
    admin_headers = login(client, "admin@example.test", "Admin123!")
    audit_response = client.get("/audit-logs", headers=admin_headers)
    assert audit_response.status_code == 200
    assert any(entry["entity_type"] == "animal" and entry["action"] == "create" for entry in audit_response.json())


def test_vet_can_only_update_animal_health_status(client: TestClient) -> None:
    vet_headers = login(client, "vet@example.test", "Vet123!")
    forbidden = client.patch("/animals/1", headers=vet_headers, json={"name": "Neuer Name"})
    assert forbidden.status_code == 403

    allowed = client.patch("/animals/1", headers=vet_headers, json={"health_status": "observation"})
    assert allowed.status_code == 200
    assert allowed.json()["health_status"] == "observation"


def test_health_records_are_restricted(client: TestClient) -> None:
    keeper_headers = login(client, "keeper@example.test", "Keeper123!")
    response = client.get("/health-records", headers=keeper_headers)
    assert response.status_code == 403

    vet_headers = login(client, "vet@example.test", "Vet123!")
    response = client.get("/health-records", headers=vet_headers)
    assert response.status_code == 200
