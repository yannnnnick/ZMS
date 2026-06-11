from __future__ import annotations

import os
from collections.abc import Sequence

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from .database import get_db, init_db
from .models import (
    Animal,
    AuditLog,
    Enclosure,
    FeedingSchedule,
    HealthRecord,
    HealthStatus,
    SafetyStatus,
    Species,
    Task,
    TaskStatus,
    User,
    UserRole,
)
from .schemas import (
    AnimalCreate,
    AnimalRead,
    AnimalUpdate,
    AuditLogRead,
    DashboardSummary,
    EnclosureCreate,
    EnclosureRead,
    FeedingScheduleCreate,
    FeedingScheduleRead,
    HealthRecordCreate,
    HealthRecordRead,
    LoginRequest,
    SpeciesCreate,
    SpeciesRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    TokenResponse,
    UserRead,
)
from .security import (
    check_login_rate_limit,
    clear_failed_logins,
    create_access_token,
    get_current_user,
    register_failed_login,
    require_roles,
    request_ip_hash,
    verify_password,
    write_audit_log,
)


def create_app(seed: bool = True, init_database: bool = True) -> FastAPI:
    app = FastAPI(title="Zoo Management Tool", version="0.1.0")

    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.on_event("startup")
    def startup() -> None:
        if init_database:
            init_db(seed=seed)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/auth/login", response_model=TokenResponse)
    def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
        identifier = payload.email.lower()
        check_login_rate_limit(identifier)
        user = db.query(User).filter(User.email == identifier).first()
        if user is None or not verify_password(payload.password, user.password_hash):
            register_failed_login(identifier)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.is_active:
            register_failed_login(identifier)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

        clear_failed_logins(identifier)
        token = create_access_token(user.email, user.role)
        write_audit_log(db, user, "login", "user", user.id, ip_hash=request_ip_hash(request))
        db.commit()
        return TokenResponse(access_token=token, role=user.role, display_name=user.display_name)

    @app.post("/auth/logout")
    def logout(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict[str, str]:
        write_audit_log(db, current_user, "logout", "user", current_user.id, ip_hash=request_ip_hash(request))
        db.commit()
        return {"status": "ok"}

    @app.get("/me", response_model=UserRead)
    def me(current_user: User = Depends(get_current_user)) -> User:
        return current_user

    @app.get("/dashboard", response_model=DashboardSummary)
    def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardSummary:
        animals_total = db.query(Animal).filter(Animal.active.is_(True)).count()
        open_tasks = db.query(Task).filter(Task.status != TaskStatus.done).count()
        due_feedings = db.query(FeedingSchedule).count()
        critical_health = db.query(Animal).filter(Animal.health_status == HealthStatus.critical, Animal.active.is_(True)).count()
        warning_enclosures = db.query(Enclosure).filter(Enclosure.safety_status != SafetyStatus.ok).count()
        recent_tasks = db.query(Task).filter(Task.status != TaskStatus.done).order_by(Task.due_at.asc()).limit(5).all()
        warning_animals = (
            db.query(Animal)
            .options(joinedload(Animal.species), joinedload(Animal.enclosure))
            .filter(Animal.health_status != HealthStatus.healthy, Animal.active.is_(True))
            .limit(5)
            .all()
        )
        enclosure_status = db.query(Enclosure).order_by(Enclosure.safety_status.desc(), Enclosure.name.asc()).limit(8).all()
        return DashboardSummary(
            animals_total=animals_total,
            open_tasks=open_tasks,
            due_feedings=due_feedings,
            critical_health=critical_health,
            warning_enclosures=warning_enclosures,
            recent_tasks=recent_tasks,
            warning_animals=warning_animals,
            enclosure_status=enclosure_status,
        )

    @app.get("/animals", response_model=list[AnimalRead])
    def list_animals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Sequence[Animal]:
        return (
            db.query(Animal)
            .options(joinedload(Animal.species), joinedload(Animal.enclosure))
            .filter(Animal.active.is_(True))
            .order_by(Animal.name.asc())
            .all()
        )

    @app.post("/animals", response_model=AnimalRead, status_code=status.HTTP_201_CREATED)
    def create_animal(
        payload: AnimalCreate,
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> Animal:
        ensure_species_and_enclosure(db, payload.species_id, payload.enclosure_id)
        animal = Animal(**payload.model_dump())
        db.add(animal)
        db.flush()
        write_audit_log(db, current_user, "create", "animal", animal.id, {"name": animal.name})
        db.commit()
        db.refresh(animal)
        return animal

    @app.get("/animals/{animal_id}", response_model=AnimalRead)
    def get_animal(
        animal_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Animal:
        animal = animal_or_404(db, animal_id)
        return animal

    @app.patch("/animals/{animal_id}", response_model=AnimalRead)
    def update_animal(
        animal_id: int,
        payload: AnimalUpdate,
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Animal:
        animal = animal_or_404(db, animal_id)
        changes = payload.model_dump(exclude_unset=True)
        if current_user.role == UserRole.vet and set(changes) - {"health_status"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vet may only update health status")
        if "species_id" in changes or "enclosure_id" in changes:
            ensure_species_and_enclosure(db, changes.get("species_id", animal.species_id), changes.get("enclosure_id", animal.enclosure_id))
        for key, value in changes.items():
            setattr(animal, key, value)
        write_audit_log(db, current_user, "update", "animal", animal.id, changes)
        db.commit()
        db.refresh(animal)
        return animal

    @app.delete("/animals/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_animal(
        animal_id: int,
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> None:
        animal = animal_or_404(db, animal_id)
        animal.active = False
        write_audit_log(db, current_user, "delete", "animal", animal.id, {"soft_delete": True})
        db.commit()
        return None

    @app.get("/species", response_model=list[SpeciesRead])
    def list_species(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Sequence[Species]:
        return db.query(Species).order_by(Species.common_name.asc()).all()

    @app.post("/species", response_model=SpeciesRead, status_code=status.HTTP_201_CREATED)
    def create_species(
        payload: SpeciesCreate,
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Species:
        species = Species(**payload.model_dump())
        db.add(species)
        db.flush()
        write_audit_log(db, current_user, "create", "species", species.id, {"common_name": species.common_name})
        db.commit()
        db.refresh(species)
        return species

    @app.get("/enclosures", response_model=list[EnclosureRead])
    def list_enclosures(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Sequence[Enclosure]:
        return db.query(Enclosure).order_by(Enclosure.name.asc()).all()

    @app.post("/enclosures", response_model=EnclosureRead, status_code=status.HTTP_201_CREATED)
    def create_enclosure(
        payload: EnclosureCreate,
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Enclosure:
        enclosure = Enclosure(**payload.model_dump())
        db.add(enclosure)
        db.flush()
        write_audit_log(db, current_user, "create", "enclosure", enclosure.id, {"name": enclosure.name})
        db.commit()
        db.refresh(enclosure)
        return enclosure

    @app.get("/feeding-schedules", response_model=list[FeedingScheduleRead])
    def list_feeding_schedules(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Sequence[FeedingSchedule]:
        return (
            db.query(FeedingSchedule)
            .options(joinedload(FeedingSchedule.animal).joinedload(Animal.species), joinedload(FeedingSchedule.animal).joinedload(Animal.enclosure))
            .order_by(FeedingSchedule.scheduled_time.asc())
            .all()
        )

    @app.post("/feeding-schedules", response_model=FeedingScheduleRead, status_code=status.HTTP_201_CREATED)
    def create_feeding_schedule(
        payload: FeedingScheduleCreate,
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> FeedingSchedule:
        animal_or_404(db, payload.animal_id)
        schedule = FeedingSchedule(**payload.model_dump())
        db.add(schedule)
        db.flush()
        write_audit_log(db, current_user, "create", "feeding_schedule", schedule.id, {"animal_id": schedule.animal_id})
        db.commit()
        db.refresh(schedule)
        return schedule

    @app.get("/health-records", response_model=list[HealthRecordRead])
    def list_health_records(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Sequence[HealthRecord]:
        return (
            db.query(HealthRecord)
            .options(
                joinedload(HealthRecord.animal).joinedload(Animal.species),
                joinedload(HealthRecord.animal).joinedload(Animal.enclosure),
                joinedload(HealthRecord.created_by),
            )
            .order_by(HealthRecord.created_at.desc())
            .all()
        )

    @app.post("/health-records", response_model=HealthRecordRead, status_code=status.HTTP_201_CREATED)
    def create_health_record(
        payload: HealthRecordCreate,
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> HealthRecord:
        animal_or_404(db, payload.animal_id)
        record = HealthRecord(**payload.model_dump(), created_by_user_id=current_user.id)
        db.add(record)
        db.flush()
        write_audit_log(db, current_user, "create", "health_record", record.id, {"animal_id": record.animal_id, "record_type": record.record_type.value})
        db.commit()
        db.refresh(record)
        return record

    @app.get("/tasks", response_model=list[TaskRead])
    def list_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Sequence[Task]:
        return db.query(Task).order_by(Task.due_at.asc()).all()

    @app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def create_task(
        payload: TaskCreate,
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Task:
        if payload.related_animal_id is not None:
            animal_or_404(db, payload.related_animal_id)
        if payload.related_enclosure_id is not None:
            enclosure_or_404(db, payload.related_enclosure_id)
        task = Task(**payload.model_dump())
        db.add(task)
        db.flush()
        write_audit_log(db, current_user, "create", "task", task.id, {"title": task.title})
        db.commit()
        db.refresh(task)
        return task

    @app.patch("/tasks/{task_id}", response_model=TaskRead)
    def update_task(
        task_id: int,
        payload: TaskUpdate,
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Task:
        task = task_or_404(db, task_id)
        changes = payload.model_dump(exclude_unset=True)
        if "related_animal_id" in changes and changes["related_animal_id"] is not None:
            animal_or_404(db, changes["related_animal_id"])
        if "related_enclosure_id" in changes and changes["related_enclosure_id"] is not None:
            enclosure_or_404(db, changes["related_enclosure_id"])
        for key, value in changes.items():
            setattr(task, key, value)
        write_audit_log(db, current_user, "update", "task", task.id, changes)
        db.commit()
        db.refresh(task)
        return task

    @app.get("/audit-logs", response_model=list[AuditLogRead])
    def list_audit_logs(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Sequence[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()

    return app


def animal_or_404(db: Session, animal_id: int) -> Animal:
    animal = (
        db.query(Animal)
        .options(joinedload(Animal.species), joinedload(Animal.enclosure))
        .filter(Animal.id == animal_id, Animal.active.is_(True))
        .first()
    )
    if animal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Animal not found")
    return animal


def species_or_404(db: Session, species_id: int) -> Species:
    species = db.get(Species, species_id)
    if species is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Species not found")
    return species


def enclosure_or_404(db: Session, enclosure_id: int) -> Enclosure:
    enclosure = db.get(Enclosure, enclosure_id)
    if enclosure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enclosure not found")
    return enclosure


def task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def ensure_species_and_enclosure(db: Session, species_id: int, enclosure_id: int) -> None:
    species_or_404(db, species_id)
    enclosure_or_404(db, enclosure_id)


app = create_app()
