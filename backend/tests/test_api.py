from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from collections.abc import Generator

os.environ.setdefault("JWT_SECRET", "test-secret-for-zms-cookie-auth-suite-32-bytes")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import create_app
from app.models import User, UserRole
from app.seed import seed_demo_data
from app.security import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, JWT_ALGORITHM, JWT_SECRET, hash_password, verify_password


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
    body = response.json()
    assert "access_token" not in body
    assert client.cookies.get(AUTH_COOKIE_NAME)
    assert client.cookies.get(CSRF_COOKIE_NAME)
    return {"X-CSRF-Token": body["csrf_token"]}


def test_login_and_dashboard(client: TestClient) -> None:
    headers = login(client, "admin@example.test", "Admin12345!")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["animals_total"] >= 5
    assert body["open_tasks"] >= 1


def test_login_rejects_wrong_password(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@example.test", "password": "Wrong12345!"})
    assert response.status_code == 401


def test_login_rejects_long_password_without_server_error(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@example.test", "password": "A" * 200})
    assert response.status_code in {400, 401, 422}
    assert response.status_code != 500


def test_long_password_can_be_hashed_and_verified() -> None:
    password = "This-Is-A-Strong-Password-12345"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_weak_password_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("short")


def test_unknown_password_hash_returns_false() -> None:
    assert verify_password("Admin12345!", "not-a-valid-password-hash") is False


def test_login_rejects_inactive_user(client: TestClient) -> None:
    session_factory = client.app.state.testing_session_factory
    db = session_factory()
    try:
        db.add(
            User(
                email="inactive@example.test",
                display_name="Inactive Demo",
                role=UserRole.viewer,
                password_hash=hash_password("Inactive12345!"),
                is_active=False,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post("/auth/login", json={"email": "inactive@example.test", "password": "Inactive12345!"})
    assert response.status_code == 403


def test_viewer_cannot_create_animal(client: TestClient) -> None:
    viewer_headers = login(client, "viewer@example.test", "Viewer12345!")
    response = client.post(
        "/animals",
        headers=viewer_headers,
        json={"name": "Testtier", "species_id": 1, "enclosure_id": 1, "sex": "unknown", "health_status": "healthy"},
    )
    assert response.status_code == 403


def test_keeper_can_create_animal_and_audit_is_written(client: TestClient) -> None:
    keeper_headers = login(client, "keeper@example.test", "Keeper12345!")
    response = client.post(
        "/animals",
        headers=keeper_headers,
        json={"name": "Nala", "species_id": 3, "enclosure_id": 3, "sex": "female", "health_status": "healthy"},
    )
    assert response.status_code == 201
    admin_headers = login(client, "admin@example.test", "Admin12345!")
    audit_response = client.get("/audit-logs", headers=admin_headers)
    assert audit_response.status_code == 200
    assert any(entry["entity_type"] == "animal" and entry["action"] == "create" for entry in audit_response.json())


def test_vet_can_only_update_animal_health_status(client: TestClient) -> None:
    vet_headers = login(client, "vet@example.test", "Vet123456!")
    forbidden = client.patch("/animals/1", headers=vet_headers, json={"name": "Neuer Name"})
    assert forbidden.status_code == 403

    allowed = client.patch("/animals/1", headers=vet_headers, json={"health_status": "observation"})
    assert allowed.status_code == 200
    assert allowed.json()["health_status"] == "observation"


def test_health_records_are_restricted(client: TestClient) -> None:
    keeper_headers = login(client, "keeper@example.test", "Keeper12345!")
    response = client.get("/health-records", headers=keeper_headers)
    assert response.status_code == 403

    vet_headers = login(client, "vet@example.test", "Vet123456!")
    response = client.get("/health-records", headers=vet_headers)
    assert response.status_code == 200


def test_login_sets_http_only_cookie_without_returning_token(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@example.test", "password": "Admin12345!"})
    assert response.status_code == 200
    assert "access_token" not in response.json()
    set_cookie = ",".join(response.headers.get_list("set-cookie"))
    assert AUTH_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_csrf_header_is_required_for_mutations(client: TestClient) -> None:
    login(client, "admin@example.test", "Admin12345!")
    response = client.post(
        "/animals",
        json={"name": "CSRF Test", "species_id": 1, "enclosure_id": 1, "sex": "unknown", "health_status": "healthy"},
    )
    assert response.status_code == 403


def test_expired_token_is_rejected(client: TestClient) -> None:
    expired_token = jwt.encode(
        {
            "sub": "admin@example.test",
            "role": "admin",
            "type": "access",
            "jti": "expired-token",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    client.cookies.set(AUTH_COOKIE_NAME, expired_token)
    response = client.get("/me")
    assert response.status_code == 401


def test_logout_revokes_existing_token(client: TestClient) -> None:
    headers = login(client, "admin@example.test", "Admin12345!")
    token = client.cookies.get(AUTH_COOKIE_NAME)
    assert token

    logout_response = client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 200

    client.cookies.set(AUTH_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, headers["X-CSRF-Token"])
    response = client.get("/me")
    assert response.status_code == 401


def test_failed_login_is_audited(client: TestClient) -> None:
    failed = client.post("/auth/login", json={"email": "admin@example.test", "password": "Wrong12345!"})
    assert failed.status_code == 401

    admin_headers = login(client, "admin@example.test", "Admin12345!")
    audit_response = client.get("/audit-logs", headers=admin_headers)
    assert audit_response.status_code == 200
    assert any(entry["action"] == "login_failed" for entry in audit_response.json())


def test_soft_deleted_animal_is_hidden_and_feeding_removed(client: TestClient) -> None:
    admin_headers = login(client, "admin@example.test", "Admin12345!")
    delete_response = client.delete("/animals/1", headers=admin_headers)
    assert delete_response.status_code == 204

    animals_response = client.get("/animals", headers=admin_headers)
    assert animals_response.status_code == 200
    assert all(animal["id"] != 1 for animal in animals_response.json())

    feedings_response = client.get("/feeding-schedules", headers=admin_headers)
    assert feedings_response.status_code == 200
    assert all(feeding["animal_id"] != 1 for feeding in feedings_response.json())


def test_viewer_cannot_list_tasks(client: TestClient) -> None:
    viewer_headers = login(client, "viewer@example.test", "Viewer12345!")
    response = client.get("/tasks", headers=viewer_headers)
    assert response.status_code == 403


def test_viewer_uses_public_map_instead_of_internal_dashboard(client: TestClient) -> None:
    viewer_headers = login(client, "viewer@example.test", "Viewer12345!")
    dashboard_response = client.get("/dashboard", headers=viewer_headers)
    assert dashboard_response.status_code == 403

    public_response = client.get("/api/public/map")
    assert public_response.status_code == 200
    body = public_response.json()
    assert body["enclosures"]
    assert "health_status" not in str(body)


def test_keeper_and_vet_see_only_assigned_animals(client: TestClient) -> None:
    admin_headers = login(client, "admin@example.test", "Admin12345!")
    admin_animals = client.get("/animals", headers=admin_headers).json()
    assert len(admin_animals) == 5

    keeper_headers = login(client, "keeper@example.test", "Keeper12345!")
    keeper_animals = client.get("/animals", headers=keeper_headers)
    assert keeper_animals.status_code == 200
    assert {animal["id"] for animal in keeper_animals.json()} == {1, 2, 3}

    vet_headers = login(client, "vet@example.test", "Vet123456!")
    vet_animals = client.get("/animals", headers=vet_headers)
    assert vet_animals.status_code == 200
    assert {animal["id"] for animal in vet_animals.json()} == {1, 3, 5}


def test_admin_can_create_animal_assignment(client: TestClient) -> None:
    admin_headers = login(client, "admin@example.test", "Admin12345!")
    response = client.post(
        "/assignments/animals",
        headers=admin_headers,
        json={"animal_id": 4, "user_id": 2, "role_type": "keeper"},
    )
    assert response.status_code == 201
    assert response.json()["animal_id"] == 4

    keeper_headers = login(client, "keeper@example.test", "Keeper12345!")
    animals_response = client.get("/animals", headers=keeper_headers)
    assert animals_response.status_code == 200
    assert 4 in {animal["id"] for animal in animals_response.json()}


def test_keeper_can_complete_care_task_and_report_condition(client: TestClient) -> None:
    keeper_headers = login(client, "keeper@example.test", "Keeper12345!")
    tasks_response = client.get("/care-tasks", headers=keeper_headers)
    assert tasks_response.status_code == 200
    task_id = tasks_response.json()[0]["id"]

    done_response = client.patch(f"/care-tasks/{task_id}", headers=keeper_headers, json={"status": "done"})
    assert done_response.status_code == 200
    assert done_response.json()["status"] == "done"

    report_response = client.post(
        "/condition-reports",
        headers=keeper_headers,
        json={
            "animal_id": 1,
            "task_id": task_id,
            "mood": "normal",
            "appetite": "low",
            "movement": "normal",
            "visible_injuries": False,
            "needs_vet_check": True,
            "notes": "<script>alert(1)</script>",
        },
    )
    assert report_response.status_code == 201
    assert "&lt;script&gt;" in report_response.json()["notes"]

    vet_headers = login(client, "vet@example.test", "Vet123456!")
    vet_tasks_response = client.get("/vet-tasks", headers=vet_headers)
    assert vet_tasks_response.status_code == 200
    assert any("Zustandsbericht" in task["title"] for task in vet_tasks_response.json())


def test_admin_economy_and_feeding_optimizer(client: TestClient) -> None:
    admin_headers = login(client, "admin@example.test", "Admin12345!")
    economy_response = client.get("/admin/economy", headers=admin_headers)
    assert economy_response.status_code == 200
    assert economy_response.json()["visitors_week"] > 0

    users_response = client.get("/users?role=keeper", headers=admin_headers)
    assert users_response.status_code == 200
    keeper_id = users_response.json()[0]["id"]
    salary_response = client.post(
        "/admin/salary-simulation",
        headers=admin_headers,
        json={"user_id": keeper_id, "start_date": str(datetime.now(timezone.utc).date() - timedelta(days=1)), "end_date": str(datetime.now(timezone.utc).date())},
    )
    assert salary_response.status_code == 200
    assert salary_response.json()["is_simulation"] is True

    optimizer_response = client.post("/admin/feeding-optimization", headers=admin_headers, json={"animal_id": 1})
    assert optimizer_response.status_code == 200
    assert optimizer_response.json()["success"] is True
    assert optimizer_response.json()["feeding_plan"]
