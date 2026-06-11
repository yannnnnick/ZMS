from __future__ import annotations

import os
import secrets
import logging
from contextlib import asynccontextmanager
from collections.abc import Sequence
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select, update
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
    SessionResponse,
    UserRead,
)
from .security import (
    clear_failed_logins,
    clear_auth_cookies,
    consume_login_attempt,
    create_csrf_token,
    create_access_token,
    CSRF_COOKIE_NAME,
    get_current_user,
    require_roles,
    request_ip_hash,
    revoke_token,
    set_auth_cookies,
    verify_password,
    write_audit_log,
)

logger = logging.getLogger(__name__)
DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def parse_cors_origins(raw_origins: str) -> list[str]:
    origins: list[str] = []
    for raw_origin in raw_origins.split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            raise RuntimeError("CORS_ORIGINS must not contain '*' when credentialed requests are enabled.")
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"Invalid CORS origin: {origin}")
        origins.append(origin)
    if not origins:
        raise RuntimeError("CORS_ORIGINS must contain at least one valid origin.")
    return origins


def require_csrf(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    allowed_origins = getattr(request.app.state, "cors_origins", [])
    if origin and origin.rstrip("/") not in allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin")

    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


def create_app(seed: bool = True, init_database: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if init_database:
            init_db(seed=seed)
        yield

    app = FastAPI(title="Zoo Management Tool", version="0.1.0", lifespan=lifespan)

    origins = parse_cors_origins(os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"))
    app.state.cors_origins = origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/auth/login", response_model=SessionResponse)
    def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> JSONResponse:
        identifier = payload.email.lower()
        consume_login_attempt(identifier)
        ip_hash = request_ip_hash(request)
        user = db.query(User).filter(User.email == identifier).first()
        if user is None or not verify_password(payload.password, user.password_hash):
            write_audit_log(
                db,
                None,
                "login_failed",
                "user",
                user.id if user else None,
                {"email": identifier, "reason": "invalid_credentials"},
                ip_hash=ip_hash,
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.is_active:
            write_audit_log(
                db,
                None,
                "login_failed",
                "user",
                user.id,
                {"email": identifier, "reason": "inactive_user"},
                ip_hash=ip_hash,
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

        clear_failed_logins(identifier)
        token = create_access_token(user.email, user.role)
        csrf_token = create_csrf_token()
        write_audit_log(db, user, "login", "user", user.id, ip_hash=ip_hash)
        db.commit()
        response = JSONResponse(
            content={"role": user.role.value, "display_name": user.display_name, "csrf_token": csrf_token}
        )
        set_auth_cookies(response, token, csrf_token)
        return response

    @app.post("/auth/logout")
    def logout(
        request: Request,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        write_audit_log(db, current_user, "logout", "user", current_user.id, ip_hash=request_ip_hash(request))
        revoke_token(getattr(request.state, "jwt_payload", {}))
        db.commit()
        response = JSONResponse(content={"status": "ok"})
        clear_auth_cookies(response)
        return response

    @app.get("/me", response_model=UserRead)
    def me(current_user: User = Depends(get_current_user)) -> User:
        return current_user

    @app.get("/dashboard", response_model=DashboardSummary)
    def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardSummary:
        counts = db.execute(
            select(
                select(func.count(Animal.id)).where(Animal.active.is_(True)).scalar_subquery().label("animals_total"),
                select(func.count(Task.id)).where(Task.status != TaskStatus.done).scalar_subquery().label("open_tasks"),
                select(func.count(FeedingSchedule.id)).scalar_subquery().label("due_feedings"),
                select(func.count(Animal.id))
                .where(Animal.health_status == HealthStatus.critical, Animal.active.is_(True))
                .scalar_subquery()
                .label("critical_health"),
                select(func.count(Enclosure.id))
                .where(Enclosure.safety_status != SafetyStatus.ok)
                .scalar_subquery()
                .label("warning_enclosures"),
            )
        ).one()
        count_map = counts._mapping
        recent_tasks = db.query(Task).filter(Task.status != TaskStatus.done).order_by(Task.due_at.asc()).limit(5).all()
        warning_animals = (
            db.query(Animal)
            .options(joinedload(Animal.species), joinedload(Animal.enclosure))
            .filter(Animal.health_status != HealthStatus.healthy, Animal.active.is_(True))
            .order_by(Animal.updated_at.desc())
            .limit(5)
            .all()
        )
        enclosure_status = db.query(Enclosure).order_by(Enclosure.safety_status.desc(), Enclosure.name.asc()).limit(8).all()
        return DashboardSummary(
            animals_total=count_map["animals_total"],
            open_tasks=count_map["open_tasks"],
            due_feedings=count_map["due_feedings"],
            critical_health=count_map["critical_health"],
            warning_enclosures=count_map["warning_enclosures"],
            recent_tasks=recent_tasks,
            warning_animals=warning_animals,
            enclosure_status=enclosure_status,
        )

    @app.get("/animals", response_model=list[AnimalRead])
    def list_animals(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Animal]:
        return (
            db.query(Animal)
            .options(joinedload(Animal.species), joinedload(Animal.enclosure))
            .filter(Animal.active.is_(True))
            .order_by(Animal.name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @app.post("/animals", response_model=AnimalRead, status_code=status.HTTP_201_CREATED)
    def create_animal(
        payload: AnimalCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> Animal:
        ensure_species_and_enclosure(db, payload.species_id, payload.enclosure_id)
        animal = Animal(**payload.model_dump(exclude={"active"}), active=True)
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
        animal = animal_or_404(db, animal_id, eager_load=True)
        return animal

    @app.patch("/animals/{animal_id}", response_model=AnimalRead)
    def update_animal(
        animal_id: int,
        payload: AnimalUpdate,
        _csrf: None = Depends(require_csrf),
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
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> None:
        animal = animal_or_404(db, animal_id)
        db.execute(delete(FeedingSchedule).where(FeedingSchedule.animal_id == animal.id))
        db.execute(update(Task).where(Task.related_animal_id == animal.id).values(related_animal_id=None))
        animal.active = False
        write_audit_log(db, current_user, "delete", "animal", animal.id, {"soft_delete": True})
        db.commit()
        return None

    @app.get("/species", response_model=list[SpeciesRead])
    def list_species(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Species]:
        return db.query(Species).order_by(Species.common_name.asc()).offset(offset).limit(limit).all()

    @app.post("/species", response_model=SpeciesRead, status_code=status.HTTP_201_CREATED)
    def create_species(
        payload: SpeciesCreate,
        _csrf: None = Depends(require_csrf),
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
    def list_enclosures(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Enclosure]:
        return db.query(Enclosure).order_by(Enclosure.name.asc()).offset(offset).limit(limit).all()

    @app.post("/enclosures", response_model=EnclosureRead, status_code=status.HTTP_201_CREATED)
    def create_enclosure(
        payload: EnclosureCreate,
        _csrf: None = Depends(require_csrf),
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
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[FeedingSchedule]:
        return (
            db.query(FeedingSchedule)
            .options(joinedload(FeedingSchedule.animal).joinedload(Animal.species), joinedload(FeedingSchedule.animal).joinedload(Animal.enclosure))
            .join(FeedingSchedule.animal)
            .filter(Animal.active.is_(True))
            .order_by(FeedingSchedule.scheduled_time.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @app.post("/feeding-schedules", response_model=FeedingScheduleRead, status_code=status.HTTP_201_CREATED)
    def create_feeding_schedule(
        payload: FeedingScheduleCreate,
        _csrf: None = Depends(require_csrf),
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
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[HealthRecord]:
        return (
            db.query(HealthRecord)
            .options(
                joinedload(HealthRecord.animal).joinedload(Animal.species),
                joinedload(HealthRecord.animal).joinedload(Animal.enclosure),
                joinedload(HealthRecord.created_by),
            )
            .join(HealthRecord.animal)
            .filter(Animal.active.is_(True))
            .order_by(HealthRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @app.post("/health-records", response_model=HealthRecordRead, status_code=status.HTTP_201_CREATED)
    def create_health_record(
        payload: HealthRecordCreate,
        _csrf: None = Depends(require_csrf),
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
    def list_tasks(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Task]:
        return db.query(Task).order_by(Task.due_at.asc()).offset(offset).limit(limit).all()

    @app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def create_task(
        payload: TaskCreate,
        _csrf: None = Depends(require_csrf),
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
        _csrf: None = Depends(require_csrf),
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

    @app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(
        task_id: int,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> None:
        task = task_or_404(db, task_id)
        db.delete(task)
        write_audit_log(db, current_user, "delete", "task", task.id, {"title": task.title})
        db.commit()
        return None

    @app.get("/audit-logs", response_model=list[AuditLogRead])
    def list_audit_logs(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return app


def animal_or_404(db: Session, animal_id: int, *, eager_load: bool = False) -> Animal:
    query = db.query(Animal).filter(Animal.id == animal_id, Animal.active.is_(True))
    if eager_load:
        query = query.options(joinedload(Animal.species), joinedload(Animal.enclosure))
    animal = query.first()
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
