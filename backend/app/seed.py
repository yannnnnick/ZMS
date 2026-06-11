from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Animal,
    AnimalAssignment,
    AnimalNutritionRequirement,
    AssignmentRoleType,
    CareTask,
    CareTaskType,
    Enclosure,
    EnclosureAssignment,
    FeedingSchedule,
    FoodItem,
    HealthRecord,
    HealthStatus,
    MapPath,
    RecordType,
    SafetyStatus,
    SalaryProfile,
    Sex,
    Species,
    Task,
    TaskStatus,
    TaskType,
    User,
    UserRole,
    VetTask,
    VetTaskPriority,
    VisitorStat,
    WorkSession,
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
                password_hash=hash_password("Admin12345!"),
            ),
            User(
                email="keeper@example.test",
                display_name="Kai Keeper",
                role=UserRole.keeper,
                password_hash=hash_password("Keeper12345!"),
            ),
            User(email="vet@example.test", display_name="Vera Vet", role=UserRole.vet, password_hash=hash_password("Vet123456!")),
            User(
                email="viewer@example.test",
                display_name="Vivian Viewer",
                role=UserRole.viewer,
                password_hash=hash_password("Viewer12345!"),
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

        savanna = Enclosure(
            name="Savanne 1",
            location="Nordbereich",
            capacity=8,
            safety_status=SafetyStatus.ok,
            map_x=80,
            map_y=80,
            map_width=220,
            map_height=130,
            public_name="Giraffen-Savanne",
            public_description="Weitlaeufige Anlage mit hohen Futterstellen und Aussichtspunkt.",
        )
        elephant_park = Enclosure(
            name="Elefantenpark",
            location="Ostbereich",
            capacity=5,
            safety_status=SafetyStatus.ok,
            map_x=360,
            map_y=70,
            map_width=240,
            map_height=150,
            public_name="Elefantenpark",
            public_description="Aussenanlage mit Badebereich und Schattenplaetzen.",
        )
        lion_area = Enclosure(
            name="Loewenanlage",
            location="Westbereich",
            capacity=4,
            safety_status=SafetyStatus.warning,
            notes="Zaunpruefung faellig.",
            map_x=80,
            map_y=280,
            map_width=210,
            map_height=125,
            public_name="Loewenfelsen",
            public_description="Felsenanlage mit geschuetzter Besucherperspektive.",
        )
        penguin_pool = Enclosure(
            name="Pinguinbecken",
            location="Suedbereich",
            capacity=24,
            safety_status=SafetyStatus.ok,
            map_x=360,
            map_y=300,
            map_width=190,
            map_height=120,
            public_name="Pinguinbecken",
            public_description="Kuehles Wasserbecken mit taeglichen Fuetterungen.",
        )
        ape_house = Enclosure(
            name="Menschenaffenhaus",
            location="Innenbereich",
            capacity=10,
            safety_status=SafetyStatus.ok,
            map_x=610,
            map_y=210,
            map_width=180,
            map_height=150,
            public_name="Menschenaffenhaus",
            public_description="Innen- und Aussenbereiche mit Kletterstruktur.",
        )
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
                AnimalAssignment(animal=animals[0], user=users[1], role_type=AssignmentRoleType.keeper, assigned_by=users[0].id),
                AnimalAssignment(animal=animals[1], user=users[1], role_type=AssignmentRoleType.keeper, assigned_by=users[0].id),
                AnimalAssignment(animal=animals[2], user=users[1], role_type=AssignmentRoleType.keeper, assigned_by=users[0].id),
                AnimalAssignment(animal=animals[0], user=users[2], role_type=AssignmentRoleType.vet, assigned_by=users[0].id),
                AnimalAssignment(animal=animals[2], user=users[2], role_type=AssignmentRoleType.vet, assigned_by=users[0].id),
                AnimalAssignment(animal=animals[4], user=users[2], role_type=AssignmentRoleType.vet, assigned_by=users[0].id),
                EnclosureAssignment(enclosure=savanna, user=users[1], assigned_by=users[0].id),
                EnclosureAssignment(enclosure=elephant_park, user=users[1], assigned_by=users[0].id),
                EnclosureAssignment(enclosure=lion_area, user=users[1], assigned_by=users[0].id),
                EnclosureAssignment(enclosure=ape_house, user=users[2], assigned_by=users[0].id),
            ]
        )
        db.add_all(
            [
                MapPath(from_enclosure=savanna, to_enclosure=elephant_park, distance_meters=160, walking_time_minutes=3),
                MapPath(from_enclosure=savanna, to_enclosure=lion_area, distance_meters=130, walking_time_minutes=2),
                MapPath(from_enclosure=lion_area, to_enclosure=penguin_pool, distance_meters=180, walking_time_minutes=4),
                MapPath(from_enclosure=penguin_pool, to_enclosure=ape_house, distance_meters=150, walking_time_minutes=3),
            ]
        )

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
        db.add_all(
            [
                CareTask(
                    title="Giraffen-Fruehfutter",
                    description="Heu auffuellen und Wasserstand pruefen.",
                    animal=animals[0],
                    enclosure=savanna,
                    assigned_to=users[1],
                    task_type=CareTaskType.feeding,
                    due_date=date.today(),
                    due_time=time(9, 0),
                    created_by=users[0].id,
                ),
                CareTask(
                    title="Loewenanlage Sichtkontrolle",
                    description="Zaun und Schleusen nach Checkliste pruefen.",
                    animal=animals[2],
                    enclosure=lion_area,
                    assigned_to=users[1],
                    task_type=CareTaskType.health_check,
                    due_date=date.today(),
                    due_time=time(12, 0),
                    created_by=users[0].id,
                ),
                CareTask(
                    title="Elefantenbad reinigen",
                    description="Beckenrand und Filterbereich kontrollieren.",
                    animal=animals[1],
                    enclosure=elephant_park,
                    assigned_to=users[1],
                    task_type=CareTaskType.cleaning,
                    due_date=date.today() + timedelta(days=1),
                    due_time=time(10, 30),
                    created_by=users[0].id,
                ),
                VetTask(
                    title="Balu Nachkontrolle",
                    description="Appetitverlust und Vitalwerte pruefen.",
                    animal=animals[4],
                    assigned_to=users[2],
                    priority=VetTaskPriority.emergency,
                    due_date=date.today(),
                    created_by=users[0].id,
                ),
                VetTask(
                    title="Aslan Hautkontrolle",
                    description="Hautreizung nach Befund erneut bewerten.",
                    animal=animals[2],
                    assigned_to=users[2],
                    priority=VetTaskPriority.medium,
                    due_date=date.today() + timedelta(days=2),
                    created_by=users[0].id,
                ),
            ]
        )
        db.add_all(
            [
                VisitorStat(date=date.today() - timedelta(days=6), visitor_count=420, ticket_revenue=630000),
                VisitorStat(date=date.today() - timedelta(days=5), visitor_count=380, ticket_revenue=570000),
                VisitorStat(date=date.today() - timedelta(days=4), visitor_count=510, ticket_revenue=765000),
                VisitorStat(date=date.today() - timedelta(days=3), visitor_count=460, ticket_revenue=690000),
                VisitorStat(date=date.today() - timedelta(days=2), visitor_count=530, ticket_revenue=795000),
                VisitorStat(date=date.today() - timedelta(days=1), visitor_count=610, ticket_revenue=915000),
                VisitorStat(date=date.today(), visitor_count=340, ticket_revenue=510000),
                WorkSession(
                    user=users[1],
                    login_at=now - timedelta(hours=6),
                    logout_at=now - timedelta(hours=1),
                    duration_minutes=300,
                    source="seed",
                ),
                WorkSession(
                    user=users[2],
                    login_at=now - timedelta(hours=4),
                    logout_at=now - timedelta(hours=1),
                    duration_minutes=180,
                    source="seed",
                ),
                SalaryProfile(user=users[1], hourly_rate=1650, monthly_base_salary=None, tax_rate_percent=20),
                SalaryProfile(user=users[2], hourly_rate=2450, monthly_base_salary=None, tax_rate_percent=24),
                SalaryProfile(user=users[0], hourly_rate=2800, monthly_base_salary=448000, tax_rate_percent=26),
                FoodItem(
                    name="Heu",
                    unit="kg",
                    cost_per_unit=70,
                    calories_per_unit=1800,
                    protein_per_unit=80,
                    fat_per_unit=20,
                    available_quantity=240,
                ),
                FoodItem(
                    name="Blaetter-Mix",
                    unit="kg",
                    cost_per_unit=140,
                    calories_per_unit=1100,
                    protein_per_unit=120,
                    fat_per_unit=15,
                    available_quantity=90,
                ),
                FoodItem(
                    name="Fisch",
                    unit="kg",
                    cost_per_unit=390,
                    calories_per_unit=1450,
                    protein_per_unit=210,
                    fat_per_unit=80,
                    available_quantity=80,
                ),
                FoodItem(
                    name="Rindfleisch",
                    unit="kg",
                    cost_per_unit=620,
                    calories_per_unit=2500,
                    protein_per_unit=260,
                    fat_per_unit=180,
                    available_quantity=65,
                ),
                AnimalNutritionRequirement(
                    species=giraffe,
                    min_calories=18000,
                    min_protein=900,
                    max_fat=900,
                    food_category="herbivore",
                ),
                AnimalNutritionRequirement(
                    species=lion,
                    min_calories=14000,
                    min_protein=1300,
                    max_fat=1300,
                    food_category="carnivore",
                ),
                AnimalNutritionRequirement(
                    species=penguin,
                    min_calories=6000,
                    min_protein=600,
                    max_fat=700,
                    food_category="fish",
                ),
            ]
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
