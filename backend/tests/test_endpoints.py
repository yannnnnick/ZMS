"""Coverage for endpoints and business rules that were previously untested:
CRUD for species/enclosures/feeding-schedules/health-records, 404 handling,
RBAC on writes, and the hardened condition-report / medical-report rules.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

Login = Callable[[str, str], dict[str, str]]

ADMIN = ("admin@example.test", "Admin12345!")
KEEPER = ("keeper@example.test", "Keeper12345!")
VET = ("vet@example.test", "Vet123456!")
VIEWER = ("viewer@example.test", "Viewer12345!")


# --- GET by id / 404 handling ----------------------------------------------


def test_get_animal_by_id_for_admin(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    response = client.get("/animals/1", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_unknown_animal_returns_404(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    assert client.get("/animals/9999", headers=headers).status_code == 404


def test_keeper_cannot_see_unassigned_animal(client: TestClient, login: Login) -> None:
    # Animal 4 (Pina) is not assigned to the keeper -> 404 (not 403) to avoid leaking existence.
    headers = login(*KEEPER)
    assert client.get("/animals/4", headers=headers).status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("patch", "/animals/9999"),
        ("delete", "/animals/9999"),
        ("patch", "/tasks/9999"),
        ("delete", "/tasks/9999"),
        ("patch", "/species/9999"),
        ("delete", "/species/9999"),
        ("patch", "/enclosures/9999"),
        ("delete", "/enclosures/9999"),
        ("patch", "/feeding-schedules/9999"),
        ("delete", "/feeding-schedules/9999"),
        ("patch", "/health-records/9999"),
        ("delete", "/health-records/9999"),
        ("patch", "/care-tasks/9999"),
        ("patch", "/vet-tasks/9999"),
    ],
)
def test_mutations_on_unknown_entities_return_404(
    client: TestClient, login: Login, method: str, path: str
) -> None:
    headers = login(*ADMIN)
    body: dict[str, object] = {} if method == "delete" else {"status": "done"}
    response = client.request(method.upper(), path, headers=headers, json=body)
    assert response.status_code == 404


# --- Species CRUD -----------------------------------------------------------


def test_admin_species_lifecycle(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    created = client.post(
        "/species",
        headers=headers,
        json={"common_name": "Rotluchs", "category": "Saeugetier"},
    )
    assert created.status_code == 201
    species_id = created.json()["id"]

    updated = client.patch(f"/species/{species_id}", headers=headers, json={"category": "Raubtier"})
    assert updated.status_code == 200
    assert updated.json()["category"] == "Raubtier"

    deleted = client.delete(f"/species/{species_id}", headers=headers)
    assert deleted.status_code == 204


def test_species_delete_blocked_when_animals_exist(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    # Species 1 has seeded animals -> deletion must be refused.
    assert client.delete("/species/1", headers=headers).status_code == 409


def test_keeper_cannot_mutate_species(client: TestClient, login: Login) -> None:
    headers = login(*KEEPER)
    assert client.patch("/species/1", headers=headers, json={"category": "x"}).status_code == 403
    assert client.delete("/species/1", headers=headers).status_code == 403


# --- Enclosure CRUD ---------------------------------------------------------


def test_admin_enclosure_update_and_delete_guard(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    created = client.post(
        "/enclosures",
        headers=headers,
        json={"name": "Testgehege", "location": "Testbereich", "capacity": 3},
    )
    assert created.status_code == 201
    enclosure_id = created.json()["id"]

    updated = client.patch(f"/enclosures/{enclosure_id}", headers=headers, json={"capacity": 9})
    assert updated.status_code == 200
    assert updated.json()["capacity"] == 9

    # Empty enclosure can be deleted; one with animals (id 1) cannot.
    assert client.delete(f"/enclosures/{enclosure_id}", headers=headers).status_code == 204
    assert client.delete("/enclosures/1", headers=headers).status_code == 409


# --- Feeding schedule CRUD --------------------------------------------------


def test_feeding_schedule_update_and_delete(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    created = client.post(
        "/feeding-schedules",
        headers=headers,
        json={
            "animal_id": 1,
            "food_type": "Heu",
            "amount": "10 kg",
            "scheduled_time": "08:00:00",
            "recurrence": "taeglich",
            "responsible_role": "keeper",
        },
    )
    assert created.status_code == 201
    schedule_id = created.json()["id"]

    updated = client.patch(f"/feeding-schedules/{schedule_id}", headers=headers, json={"amount": "12 kg"})
    assert updated.status_code == 200
    assert updated.json()["amount"] == "12 kg"

    assert client.delete(f"/feeding-schedules/{schedule_id}", headers=headers).status_code == 204


# --- Health record CRUD -----------------------------------------------------


def test_health_record_update_and_delete(client: TestClient, login: Login) -> None:
    vet_headers = login(*VET)
    created = client.post(
        "/health-records",
        headers=vet_headers,
        json={"animal_id": 1, "record_type": "note", "description": "Routinekontrolle"},
    )
    assert created.status_code == 201
    record_id = created.json()["id"]

    updated = client.patch(
        f"/health-records/{record_id}", headers=vet_headers, json={"description": "Aktualisierte Notiz"}
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Aktualisierte Notiz"

    # Only admin may delete health records.
    assert client.delete(f"/health-records/{record_id}", headers=vet_headers).status_code == 403
    admin_headers = login(*ADMIN)
    assert client.delete(f"/health-records/{record_id}", headers=admin_headers).status_code == 204


# --- Task creation rules ----------------------------------------------------


def test_keeper_can_create_task_for_own_role(client: TestClient, login: Login) -> None:
    headers = login(*KEEPER)
    response = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Gehege reinigen",
            "task_type": "cleaning",
            "assigned_role": "keeper",
            "due_at": "2099-01-01T09:00:00+00:00",
        },
    )
    assert response.status_code == 201


def test_keeper_cannot_assign_task_to_other_role(client: TestClient, login: Login) -> None:
    headers = login(*KEEPER)
    response = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Tierarzt-Aufgabe",
            "task_type": "checkup",
            "assigned_role": "vet",
            "due_at": "2099-01-01T09:00:00+00:00",
        },
    )
    assert response.status_code == 403


# --- Hardened business rules ------------------------------------------------


def test_condition_report_without_assigned_vet_is_rejected(client: TestClient, login: Login) -> None:
    admin_headers = login(*ADMIN)
    # Create a fresh animal with no vet assignment.
    created = client.post(
        "/animals",
        headers=admin_headers,
        json={"name": "Solo", "species_id": 1, "enclosure_id": 1, "sex": "unknown", "health_status": "healthy"},
    )
    assert created.status_code == 201
    animal_id = created.json()["id"]

    report = client.post(
        "/condition-reports",
        headers=admin_headers,
        json={
            "animal_id": animal_id,
            "mood": "nervous",
            "appetite": "refused",
            "movement": "weak",
            "needs_vet_check": True,
        },
    )
    assert report.status_code == 409


def test_medical_report_does_not_downgrade_critical_animal(client: TestClient, login: Login) -> None:
    vet_headers = login(*VET)
    # Animal 5 (Balu) is seeded as critical and assigned to the vet.
    response = client.post(
        "/medical-reports",
        headers=vet_headers,
        json={"animal_id": 5, "diagnosis": "Stabil, keine Nachsorge noetig", "follow_up_required": False},
    )
    assert response.status_code == 201

    admin_headers = login(*ADMIN)
    animal = client.get("/animals/5", headers=admin_headers)
    assert animal.status_code == 200
    assert animal.json()["health_status"] == "critical"


def test_medical_report_escalates_healthy_animal(client: TestClient, login: Login) -> None:
    vet_headers = login(*VET)
    # Animal 1 (Kito) is healthy and assigned to the vet; a follow-up report escalates to treatment.
    response = client.post(
        "/medical-reports",
        headers=vet_headers,
        json={"animal_id": 1, "diagnosis": "Behandlung erforderlich", "follow_up_required": True},
    )
    assert response.status_code == 201

    admin_headers = login(*ADMIN)
    animal = client.get("/animals/1", headers=admin_headers).json()
    assert animal["health_status"] == "treatment"


def test_salary_simulation_respects_zero_tax_rate(client: TestClient, login: Login) -> None:
    admin_headers = login(*ADMIN)
    users = client.get("/users?role=keeper", headers=admin_headers).json()
    keeper_id = users[0]["id"]

    # Force a 0% tax rate; the simulation must report zero deductions (not the 20% default).
    factory = client.app.state.testing_session_factory
    from app.models import SalaryProfile

    db = factory()
    try:
        profile = db.query(SalaryProfile).filter(SalaryProfile.user_id == keeper_id).first()
        profile.tax_rate_percent = 0
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/admin/salary-simulation",
        headers=admin_headers,
        json={"user_id": keeper_id, "start_date": "2026-06-01", "end_date": "2026-06-30"},
    )
    assert response.status_code == 200
    assert response.json()["estimated_deductions"] == 0


def test_pagination_limit_is_enforced(client: TestClient, login: Login) -> None:
    headers = login(*ADMIN)
    response = client.get("/animals?limit=2", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) <= 2

    # Limits above the cap are rejected by validation.
    assert client.get("/animals?limit=9999", headers=headers).status_code == 422
