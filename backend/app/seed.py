from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Animal,
    Enclosure,
    FeedingSchedule,
    HealthRecord,
    HealthStatus,
    RecordType,
    SafetyStatus,
    Sex,
    Species,
    Task,
    TaskStatus,
    TaskType,
    User,
    UserRole,
)
from .security import hash_password


def seed_demo_data(session_factory: sessionmaker[Session]) -> None:
    db = session_factory()
    try:
        if db.query(User).first():
            return

        users = [
            User(
                email="admin@example.test",
                display_name="Ada Admin",
                role=UserRole.admin,
                password_hash=hash_password("Admin123!"),
            ),
            User(
                email="keeper@example.test",
                display_name="Kai Keeper",
                role=UserRole.keeper,
                password_hash=hash_password("Keeper123!"),
            ),
            User(email="vet@example.test", display_name="Vera Vet", role=UserRole.vet, password_hash=hash_password("Vet123!")),
            User(
                email="viewer@example.test",
                display_name="Vivian Viewer",
                role=UserRole.viewer,
                password_hash=hash_password("Viewer123!"),
            ),
        ]
        db.add_all(users)

        giraffe = Species(
            common_name="Netzgiraffe",
            scientific_name="Giraffa reticulata",
            category="Saeugetier",
            conservation_status="Gefaehrdet",
            husbandry_notes="Hohe Futterraufen und ruhige Rueckzugsbereiche einplanen.",
        )
        elephant = Species(
            common_name="Afrikanischer Elefant",
            scientific_name="Loxodonta africana",
            category="Saeugetier",
            conservation_status="Stark gefaehrdet",
        )
        lion = Species(common_name="Afrikanischer Loewe", scientific_name="Panthera leo", category="Saeugetier")
        penguin = Species(common_name="Brillenpinguin", scientific_name="Spheniscus demersus", category="Vogel")
        gorilla = Species(common_name="Westlicher Flachlandgorilla", scientific_name="Gorilla gorilla gorilla", category="Saeugetier")
        db.add_all([giraffe, elephant, lion, penguin, gorilla])

        savanna = Enclosure(name="Savanne 1", location="Nordbereich", capacity=8, safety_status=SafetyStatus.ok)
        elephant_park = Enclosure(name="Elefantenpark", location="Ostbereich", capacity=5, safety_status=SafetyStatus.ok)
        lion_area = Enclosure(
            name="Loewenanlage", location="Westbereich", capacity=4, safety_status=SafetyStatus.warning, notes="Zaunpruefung faellig."
        )
        penguin_pool = Enclosure(name="Pinguinbecken", location="Suedbereich", capacity=24, safety_status=SafetyStatus.ok)
        ape_house = Enclosure(name="Menschenaffenhaus", location="Innenbereich", capacity=10, safety_status=SafetyStatus.ok)
        db.add_all([savanna, elephant_park, lion_area, penguin_pool, ape_house])
        db.flush()

        animals = [
            Animal(name="Kito", species=giraffe, enclosure=savanna, birth_date=date(2018, 4, 21), sex=Sex.male),
            Animal(name="Maya", species=elephant, enclosure=elephant_park, birth_date=date(2003, 7, 2), sex=Sex.female),
            Animal(
                name="Aslan",
                species=lion,
                enclosure=lion_area,
                birth_date=date(2019, 9, 15),
                sex=Sex.male,
                health_status=HealthStatus.observation,
            ),
            Animal(name="Pina", species=penguin, enclosure=penguin_pool, birth_date=date(2021, 1, 9), sex=Sex.female),
            Animal(
                name="Balu",
                species=gorilla,
                enclosure=ape_house,
                birth_date=date(2011, 11, 30),
                sex=Sex.male,
                health_status=HealthStatus.critical,
            ),
        ]
        db.add_all(animals)
        db.flush()

        db.add_all(
            [
                FeedingSchedule(
                    animal=animals[0],
                    food_type="Heu/Blaetter",
                    amount="15 kg",
                    scheduled_time=time(9, 0),
                    recurrence="taeglich",
                    responsible_role=UserRole.keeper,
                ),
                FeedingSchedule(
                    animal=animals[2],
                    food_type="Rindfleisch",
                    amount="6 kg",
                    scheduled_time=time(8, 30),
                    recurrence="taeglich",
                    responsible_role=UserRole.keeper,
                ),
                FeedingSchedule(
                    animal=animals[3],
                    food_type="Fisch",
                    amount="4 kg",
                    scheduled_time=time(10, 0),
                    recurrence="taeglich",
                    responsible_role=UserRole.keeper,
                ),
            ]
        )

        now = datetime.now(timezone.utc)
        db.add_all(
            [
                HealthRecord(
                    animal=animals[4],
                    created_by=users[2],
                    record_type=RecordType.checkup,
                    description="Appetitverlust seit zwei Tagen, engmaschige Beobachtung.",
                    next_check_date=date.today() + timedelta(days=1),
                ),
                HealthRecord(
                    animal=animals[2],
                    created_by=users[2],
                    record_type=RecordType.note,
                    description="Leichte Hautreizung, Kontrolle beim naechsten Rundgang.",
                    next_check_date=date.today() + timedelta(days=3),
                ),
            ]
        )
        db.add_all(
            [
                Task(
                    title="Medikation vorbereiten - Balu",
                    description="Nach tieraerztlichem Plan vorbereiten.",
                    task_type=TaskType.checkup,
                    assigned_role=UserRole.vet,
                    due_at=now + timedelta(hours=2),
                    status=TaskStatus.open,
                    related_animal=animals[4],
                ),
                Task(
                    title="Zaunpruefung Loewenanlage",
                    description="Warnstatus pruefen und dokumentieren.",
                    task_type=TaskType.maintenance,
                    assigned_role=UserRole.keeper,
                    due_at=now + timedelta(hours=4),
                    status=TaskStatus.open,
                    related_enclosure=lion_area,
                ),
                Task(
                    title="Pinguinbecken reinigen",
                    description="Standardreinigung und Wasserqualitaet erfassen.",
                    task_type=TaskType.cleaning,
                    assigned_role=UserRole.keeper,
                    due_at=now + timedelta(days=1),
                    status=TaskStatus.in_progress,
                    related_enclosure=penguin_pool,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

