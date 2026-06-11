from __future__ import annotations

import os
import secrets
import logging
import math
from contextlib import asynccontextmanager
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, update
from sqlalchemy.orm import Session, joinedload

from .database import get_db, init_db
from .models import (
    Animal,
    AnimalAssignment,
    AnimalConditionReport,
    AnimalNutritionRequirement,
    AssignmentRoleType,
    AuditLog,
    CareTask,
    CareTaskStatus,
    Enclosure,
    EnclosureAssignment,
    FeedingSchedule,
    FoodItem,
    FeedingPlan,
    HealthRecord,
    HealthStatus,
    MapPath,
    MedicalReport,
    SafetyStatus,
    SalaryProfile,
    Species,
    Task,
    TaskStatus,
    User,
    UserRole,
    VetTask,
    VetTaskPriority,
    VetTaskStatus,
    VisitorStat,
    WorkSession,
    utcnow,
)
from .schemas import (
    AnimalCreate,
    AnimalAssignmentCreate,
    AnimalAssignmentRead,
    AnimalConditionReportCreate,
    AnimalConditionReportRead,
    AnimalRead,
    AnimalUpdate,
    AuditLogRead,
    CareTaskCreate,
    CareTaskRead,
    CareTaskUpdate,
    DashboardSummary,
    EnclosureCreate,
    EnclosureAssignmentCreate,
    EnclosureAssignmentRead,
    EnclosureRead,
    EnclosureUpdate,
    EconomySummary,
    FeedingScheduleCreate,
    FeedingScheduleRead,
    FeedingScheduleUpdate,
    FeedingOptimizationRequest,
    FeedingOptimizationResponse,
    FeedingOptimizationItem,
    HealthRecordCreate,
    HealthRecordRead,
    HealthRecordUpdate,
    LoginRequest,
    MedicalReportCreate,
    MedicalReportRead,
    PublicZooMapRead,
    SpeciesCreate,
    SpeciesRead,
    SpeciesUpdate,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    SessionResponse,
    SalarySimulationRequest,
    SalarySimulationResponse,
    UserRead,
    VetTaskCreate,
    VetTaskRead,
    VetTaskUpdate,
)
from .security import (
    clear_failed_logins,
    clear_auth_cookies,
    consume_login_attempt,
    enforce_public_rate_limit,
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

# Ordered from least to most severe. Used to ensure automatic side effects never
# silently downgrade an animal that is already in a more serious health state.
HEALTH_SEVERITY = {
    HealthStatus.healthy: 0,
    HealthStatus.observation: 1,
    HealthStatus.treatment: 2,
    HealthStatus.critical: 3,
}


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
        db.add(WorkSession(user_id=user.id, login_at=utcnow(), source="login"))
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
        open_session = (
            db.query(WorkSession)
            .filter(WorkSession.user_id == current_user.id, WorkSession.logout_at.is_(None))
            .order_by(WorkSession.login_at.desc())
            .first()
        )
        if open_session is not None:
            open_session.logout_at = utcnow()
            login_at = open_session.login_at
            if login_at.tzinfo is None:
                login_at = login_at.replace(tzinfo=timezone.utc)
            open_session.duration_minutes = max(
                0, int((open_session.logout_at - login_at).total_seconds() // 60)
            )
        revoke_token(getattr(request.state, "jwt_payload", {}))
        db.commit()
        response = JSONResponse(content={"status": "ok"})
        clear_auth_cookies(response)
        return response

    @app.get("/me", response_model=UserRead)
    def me(current_user: User = Depends(get_current_user)) -> User:
        return current_user

    @app.get("/dashboard", response_model=DashboardSummary)
    def dashboard(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> DashboardSummary:
        animal_query = animals_for_user(db, current_user)
        task_query = tasks_for_user(db, current_user).filter(Task.status != TaskStatus.done)
        feeding_query = feeding_schedules_for_user(db, current_user)
        enclosure_query = enclosures_for_user(db, current_user)

        recent_tasks = task_query.order_by(Task.due_at.asc()).limit(5).all()
        warning_animals = (
            animal_query.options(joinedload(Animal.species), joinedload(Animal.enclosure))
            .filter(Animal.health_status != HealthStatus.healthy)
            .order_by(Animal.updated_at.desc())
            .limit(5)
            .all()
        )
        enclosure_status = enclosure_query.order_by(Enclosure.safety_status.desc(), Enclosure.name.asc()).limit(8).all()
        return DashboardSummary(
            animals_total=animal_query.count(),
            open_tasks=task_query.count(),
            due_feedings=feeding_query.count(),
            critical_health=animal_query.filter(Animal.health_status == HealthStatus.critical).count(),
            warning_enclosures=enclosure_query.filter(Enclosure.safety_status != SafetyStatus.ok).count(),
            recent_tasks=recent_tasks,
            warning_animals=warning_animals,
            enclosure_status=enclosure_status,
        )

    @app.get("/animals", response_model=list[AnimalRead])
    def list_animals(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Animal]:
        return (
            animals_for_user(db, current_user)
            .options(joinedload(Animal.species), joinedload(Animal.enclosure))
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
        if current_user.role == UserRole.keeper:
            db.add(
                AnimalAssignment(
                    animal_id=animal.id,
                    user_id=current_user.id,
                    role_type=AssignmentRoleType.keeper,
                    assigned_by=current_user.id,
                )
            )
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
        animal = animal_or_404(db, animal_id, current_user=current_user, eager_load=True)
        return animal

    @app.patch("/animals/{animal_id}", response_model=AnimalRead)
    def update_animal(
        animal_id: int,
        payload: AnimalUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Animal:
        animal = animal_or_404(db, animal_id, current_user=current_user)
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
        open_care = (
            db.query(CareTask)
            .filter(CareTask.animal_id == animal.id, CareTask.status == CareTaskStatus.open)
            .count()
        )
        open_vet = (
            db.query(VetTask)
            .filter(VetTask.animal_id == animal.id, VetTask.status == VetTaskStatus.open)
            .count()
        )
        if open_care or open_vet:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot archive an animal that still has open care or vet tasks",
            )
        # Soft-delete only: setting active=False hides the animal and (via the active
        # filter on related queries) its feeding schedules, without destroying historical
        # records. Generic tasks lose their animal reference to avoid dangling pointers.
        db.execute(update(Task).where(Task.related_animal_id == animal.id).values(related_animal_id=None))
        animal.active = False
        write_audit_log(db, current_user, "delete", "animal", animal.id, {"soft_delete": True})
        db.commit()
        return None

    @app.get("/species", response_model=list[SpeciesRead])
    def list_species(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
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

    @app.patch("/species/{species_id}", response_model=SpeciesRead)
    def update_species(
        species_id: int,
        payload: SpeciesUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Species:
        species = species_or_404(db, species_id)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(species, key, value)
        write_audit_log(db, current_user, "update", "species", species.id, changes)
        db.commit()
        db.refresh(species)
        return species

    @app.delete("/species/{species_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_species(
        species_id: int,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> None:
        species = species_or_404(db, species_id)
        dependent_animals = db.query(Animal).filter(Animal.species_id == species.id).count()
        if dependent_animals:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a species that still has animals",
            )
        db.delete(species)
        write_audit_log(db, current_user, "delete", "species", species.id, {"common_name": species.common_name})
        db.commit()
        return None

    @app.get("/enclosures", response_model=list[EnclosureRead])
    def list_enclosures(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Enclosure]:
        return enclosures_for_user(db, current_user).order_by(Enclosure.name.asc()).offset(offset).limit(limit).all()

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

    @app.patch("/enclosures/{enclosure_id}", response_model=EnclosureRead)
    def update_enclosure(
        enclosure_id: int,
        payload: EnclosureUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Enclosure:
        enclosure = enclosure_or_404(db, enclosure_id)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(enclosure, key, value)
        write_audit_log(db, current_user, "update", "enclosure", enclosure.id, changes)
        db.commit()
        db.refresh(enclosure)
        return enclosure

    @app.delete("/enclosures/{enclosure_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_enclosure(
        enclosure_id: int,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> None:
        enclosure = enclosure_or_404(db, enclosure_id)
        dependent_animals = db.query(Animal).filter(Animal.enclosure_id == enclosure.id).count()
        if dependent_animals:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete an enclosure that still houses animals",
            )
        db.delete(enclosure)
        write_audit_log(db, current_user, "delete", "enclosure", enclosure.id, {"name": enclosure.name})
        db.commit()
        return None

    @app.get("/feeding-schedules", response_model=list[FeedingScheduleRead])
    def list_feeding_schedules(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[FeedingSchedule]:
        return (
            feeding_schedules_for_user(db, current_user)
            .options(joinedload(FeedingSchedule.animal).joinedload(Animal.species), joinedload(FeedingSchedule.animal).joinedload(Animal.enclosure))
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
        animal_or_404(db, payload.animal_id, current_user=current_user)
        schedule = FeedingSchedule(**payload.model_dump())
        db.add(schedule)
        db.flush()
        write_audit_log(db, current_user, "create", "feeding_schedule", schedule.id, {"animal_id": schedule.animal_id})
        db.commit()
        db.refresh(schedule)
        return schedule

    @app.patch("/feeding-schedules/{schedule_id}", response_model=FeedingScheduleRead)
    def update_feeding_schedule(
        schedule_id: int,
        payload: FeedingScheduleUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> FeedingSchedule:
        schedule = feeding_schedule_or_404(db, schedule_id, current_user=current_user)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(schedule, key, value)
        write_audit_log(db, current_user, "update", "feeding_schedule", schedule.id, changes)
        db.commit()
        db.refresh(schedule)
        return schedule

    @app.delete("/feeding-schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_feeding_schedule(
        schedule_id: int,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> None:
        schedule = feeding_schedule_or_404(db, schedule_id, current_user=current_user)
        db.delete(schedule)
        write_audit_log(db, current_user, "delete", "feeding_schedule", schedule.id, {"animal_id": schedule.animal_id})
        db.commit()
        return None

    @app.get("/health-records", response_model=list[HealthRecordRead])
    def list_health_records(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[HealthRecord]:
        return (
            health_records_for_user(db, current_user)
            .options(
                joinedload(HealthRecord.animal).joinedload(Animal.species),
                joinedload(HealthRecord.animal).joinedload(Animal.enclosure),
                joinedload(HealthRecord.created_by),
            )
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
        animal_or_404(db, payload.animal_id, current_user=current_user)
        record = HealthRecord(**payload.model_dump(), created_by_user_id=current_user.id)
        db.add(record)
        db.flush()
        write_audit_log(db, current_user, "create", "health_record", record.id, {"animal_id": record.animal_id, "record_type": record.record_type.value})
        db.commit()
        db.refresh(record)
        return record

    @app.patch("/health-records/{record_id}", response_model=HealthRecordRead)
    def update_health_record(
        record_id: int,
        payload: HealthRecordUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> HealthRecord:
        record = health_record_or_404(db, record_id, current_user=current_user)
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(record, key, value)
        write_audit_log(db, current_user, "update", "health_record", record.id, changes)
        db.commit()
        db.refresh(record)
        return record

    @app.delete("/health-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_health_record(
        record_id: int,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> None:
        record = health_record_or_404(db, record_id, current_user=current_user)
        db.delete(record)
        write_audit_log(db, current_user, "delete", "health_record", record.id, {"animal_id": record.animal_id})
        db.commit()
        return None

    @app.get("/tasks", response_model=list[TaskRead])
    def list_tasks(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[Task]:
        return (
            tasks_for_user(db, current_user)
            .options(
                joinedload(Task.related_animal).joinedload(Animal.species),
                joinedload(Task.related_enclosure),
            )
            .order_by(Task.due_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def create_task(
        payload: TaskCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Task:
        if payload.related_animal_id is not None:
            animal_or_404(db, payload.related_animal_id, current_user=current_user)
        if payload.related_enclosure_id is not None:
            enclosure_or_404(db, payload.related_enclosure_id)
        if current_user.role != UserRole.admin and payload.assigned_role != current_user.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign tasks to another role")
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
        task = task_or_404(db, task_id, current_user=current_user)
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
        task = task_or_404(db, task_id, current_user=current_user)
        db.delete(task)
        write_audit_log(db, current_user, "delete", "task", task.id, {"title": task.title})
        db.commit()
        return None

    @app.get("/users", response_model=list[UserRead])
    def list_users(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
        role: UserRole | None = Query(default=None),
    ) -> Sequence[User]:
        query = db.query(User).filter(User.is_active.is_(True))
        if role is not None:
            query = query.filter(User.role == role)
        return query.order_by(User.display_name.asc()).all()

    @app.get("/assignments/animals", response_model=list[AnimalAssignmentRead])
    def list_animal_assignments(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Sequence[AnimalAssignment]:
        return (
            db.query(AnimalAssignment)
            .options(
                joinedload(AnimalAssignment.user),
                joinedload(AnimalAssignment.animal).joinedload(Animal.species),
                joinedload(AnimalAssignment.animal).joinedload(Animal.enclosure),
            )
            .filter(AnimalAssignment.active.is_(True))
            .order_by(AnimalAssignment.created_at.desc())
            .all()
        )

    @app.post("/assignments/animals", response_model=AnimalAssignmentRead, status_code=status.HTTP_201_CREATED)
    def create_animal_assignment(
        payload: AnimalAssignmentCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> AnimalAssignment:
        animal_or_404(db, payload.animal_id)
        user = user_or_404(db, payload.user_id)
        if user.role.value != payload.role_type.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User role does not match assignment role")
        assignment = (
            db.query(AnimalAssignment)
            .filter(
                AnimalAssignment.animal_id == payload.animal_id,
                AnimalAssignment.user_id == payload.user_id,
                AnimalAssignment.role_type == payload.role_type,
                AnimalAssignment.active.is_(True),
            )
            .first()
        )
        if assignment is None:
            assignment = AnimalAssignment(**payload.model_dump(), assigned_by=current_user.id)
            db.add(assignment)
            db.flush()
        write_audit_log(
            db,
            current_user,
            "assign",
            "animal",
            payload.animal_id,
            {"user_id": payload.user_id, "role_type": payload.role_type.value},
        )
        db.commit()
        db.refresh(assignment)
        return assignment

    @app.get("/assignments/enclosures", response_model=list[EnclosureAssignmentRead])
    def list_enclosure_assignments(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> Sequence[EnclosureAssignment]:
        return (
            db.query(EnclosureAssignment)
            .options(joinedload(EnclosureAssignment.user), joinedload(EnclosureAssignment.enclosure))
            .filter(EnclosureAssignment.active.is_(True))
            .order_by(EnclosureAssignment.created_at.desc())
            .all()
        )

    @app.post("/assignments/enclosures", response_model=EnclosureAssignmentRead, status_code=status.HTTP_201_CREATED)
    def create_enclosure_assignment(
        payload: EnclosureAssignmentCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> EnclosureAssignment:
        enclosure_or_404(db, payload.enclosure_id)
        user = user_or_404(db, payload.user_id)
        if user.role not in {UserRole.keeper, UserRole.vet}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only keeper and vet users can be assigned")
        assignment = (
            db.query(EnclosureAssignment)
            .filter(
                EnclosureAssignment.enclosure_id == payload.enclosure_id,
                EnclosureAssignment.user_id == payload.user_id,
                EnclosureAssignment.active.is_(True),
            )
            .first()
        )
        if assignment is None:
            assignment = EnclosureAssignment(**payload.model_dump(), assigned_by=current_user.id)
            db.add(assignment)
            db.flush()
        write_audit_log(db, current_user, "assign", "enclosure", payload.enclosure_id, {"user_id": payload.user_id})
        db.commit()
        db.refresh(assignment)
        return assignment

    @app.get("/care-tasks", response_model=list[CareTaskRead])
    def list_care_tasks(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
        due_date: date | None = Query(default=None),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[CareTask]:
        query = care_tasks_for_user(db, current_user).options(
            joinedload(CareTask.animal).joinedload(Animal.species),
            joinedload(CareTask.animal).joinedload(Animal.enclosure),
            joinedload(CareTask.enclosure),
            joinedload(CareTask.assigned_to),
        )
        if due_date is not None:
            query = query.filter(CareTask.due_date == due_date)
        return query.order_by(CareTask.due_date.asc(), CareTask.due_time.asc()).offset(offset).limit(limit).all()

    @app.post("/care-tasks", response_model=CareTaskRead, status_code=status.HTTP_201_CREATED)
    def create_care_task(
        payload: CareTaskCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> CareTask:
        assignee = user_or_404(db, payload.assigned_to_user_id)
        if assignee.role != UserRole.keeper:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Care tasks must be assigned to keepers")
        if current_user.role == UserRole.keeper and payload.assigned_to_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keeper may only create own care tasks")
        if payload.animal_id is not None:
            animal_or_404(db, payload.animal_id, current_user=current_user)
        if payload.enclosure_id is not None:
            enclosure_or_404(db, payload.enclosure_id)
        task = CareTask(**payload.model_dump(), created_by=current_user.id)
        db.add(task)
        db.flush()
        write_audit_log(db, current_user, "create", "care_task", task.id, {"title": task.title})
        db.commit()
        db.refresh(task)
        return task

    @app.patch("/care-tasks/{task_id}", response_model=CareTaskRead)
    def update_care_task(
        task_id: int,
        payload: CareTaskUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> CareTask:
        task = care_task_or_404(db, task_id, current_user=current_user)
        changes = payload.model_dump(exclude_unset=True)
        if current_user.role != UserRole.admin:
            forbidden_fields = {"assigned_to_user_id", "title", "description", "task_type", "due_date", "due_time"}
            if set(changes) & forbidden_fields:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keeper may only update task status")
        if "assigned_to_user_id" in changes:
            assignee = user_or_404(db, changes["assigned_to_user_id"])
            if assignee.role != UserRole.keeper:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Care tasks must be assigned to keepers")
        for key, value in changes.items():
            setattr(task, key, value)
        if changes.get("status") == CareTaskStatus.done:
            task.completed_at = utcnow()
        write_audit_log(db, current_user, "update", "care_task", task.id, changes)
        db.commit()
        db.refresh(task)
        return task

    @app.post("/condition-reports", response_model=AnimalConditionReportRead, status_code=status.HTTP_201_CREATED)
    def create_condition_report(
        payload: AnimalConditionReportCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper)),
        db: Session = Depends(get_db),
    ) -> AnimalConditionReport:
        animal = animal_or_404(db, payload.animal_id, current_user=current_user)
        task = None
        if payload.task_id is not None:
            task = care_task_or_404(db, payload.task_id, current_user=current_user)
            if task.animal_id is not None and task.animal_id != payload.animal_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task belongs to another animal")
        report = AnimalConditionReport(**payload.model_dump(), created_by_user_id=current_user.id)
        db.add(report)
        if task is not None:
            task.status = CareTaskStatus.done
            task.completed_at = utcnow()
        if payload.needs_vet_check:
            vet_user = assigned_vet_for_animal(db, animal.id)
            if vet_user is None:
                # Fail loudly instead of silently dropping the escalation: a keeper must
                # never believe a vet was notified when no vet is available for the animal.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No veterinarian is assigned to this animal; cannot escalate for a vet check",
                )
            animal.health_status = (
                HealthStatus.observation if animal.health_status == HealthStatus.healthy else animal.health_status
            )
            db.add(
                VetTask(
                    title=f"Zustandsbericht pruefen - {animal.name}",
                    description=payload.notes,
                    animal_id=animal.id,
                    assigned_to_user_id=vet_user.id,
                    priority=VetTaskPriority.high if payload.visible_injuries else VetTaskPriority.medium,
                    due_date=date.today() + timedelta(days=1),
                    created_by=current_user.id,
                )
            )
        db.flush()
        write_audit_log(
            db,
            current_user,
            "create",
            "condition_report",
            report.id,
            {"animal_id": report.animal_id, "needs_vet_check": report.needs_vet_check},
        )
        db.commit()
        db.refresh(report)
        return report

    @app.get("/condition-reports", response_model=list[AnimalConditionReportRead])
    def list_condition_reports(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.keeper, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Sequence[AnimalConditionReport]:
        query = db.query(AnimalConditionReport).options(
            joinedload(AnimalConditionReport.animal).joinedload(Animal.species),
            joinedload(AnimalConditionReport.animal).joinedload(Animal.enclosure),
            joinedload(AnimalConditionReport.created_by),
        )
        if current_user.role in {UserRole.keeper, UserRole.vet}:
            query = query.join(AnimalConditionReport.animal).filter(assignment_filter_for_user(current_user))
        return query.order_by(AnimalConditionReport.created_at.desc()).limit(MAX_PAGE_LIMIT).all()

    @app.get("/vet-tasks", response_model=list[VetTaskRead])
    def list_vet_tasks(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
        due_date: date | None = Query(default=None),
        offset: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[VetTask]:
        query = vet_tasks_for_user(db, current_user).options(
            joinedload(VetTask.animal).joinedload(Animal.species),
            joinedload(VetTask.animal).joinedload(Animal.enclosure),
            joinedload(VetTask.assigned_to),
        )
        if due_date is not None:
            query = query.filter(VetTask.due_date == due_date)
        return query.order_by(VetTask.due_date.asc(), VetTask.id.asc()).offset(offset).limit(limit).all()

    @app.post("/vet-tasks", response_model=VetTaskRead, status_code=status.HTTP_201_CREATED)
    def create_vet_task(
        payload: VetTaskCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> VetTask:
        assignee = user_or_404(db, payload.assigned_to_user_id)
        if assignee.role != UserRole.vet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vet tasks must be assigned to vets")
        if current_user.role == UserRole.vet and payload.assigned_to_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vet may only create own vet tasks")
        animal_or_404(db, payload.animal_id, current_user=current_user)
        task = VetTask(**payload.model_dump(), created_by=current_user.id)
        db.add(task)
        db.flush()
        write_audit_log(db, current_user, "create", "vet_task", task.id, {"title": task.title})
        db.commit()
        db.refresh(task)
        return task

    @app.patch("/vet-tasks/{task_id}", response_model=VetTaskRead)
    def update_vet_task(
        task_id: int,
        payload: VetTaskUpdate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> VetTask:
        task = vet_task_or_404(db, task_id, current_user=current_user)
        changes = payload.model_dump(exclude_unset=True)
        if current_user.role != UserRole.admin:
            forbidden_fields = {"assigned_to_user_id", "title", "description", "priority", "due_date"}
            if set(changes) & forbidden_fields:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vet may only update task status")
        if "assigned_to_user_id" in changes:
            assignee = user_or_404(db, changes["assigned_to_user_id"])
            if assignee.role != UserRole.vet:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vet tasks must be assigned to vets")
        for key, value in changes.items():
            setattr(task, key, value)
        write_audit_log(db, current_user, "update", "vet_task", task.id, changes)
        db.commit()
        db.refresh(task)
        return task

    @app.get("/medical-reports", response_model=list[MedicalReportRead])
    def list_medical_reports(
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> Sequence[MedicalReport]:
        query = db.query(MedicalReport).options(
            joinedload(MedicalReport.animal).joinedload(Animal.species),
            joinedload(MedicalReport.animal).joinedload(Animal.enclosure),
            joinedload(MedicalReport.vet),
        )
        if current_user.role == UserRole.vet:
            query = query.filter(MedicalReport.vet_user_id == current_user.id)
        return query.order_by(MedicalReport.created_at.desc()).limit(MAX_PAGE_LIMIT).all()

    @app.post("/medical-reports", response_model=MedicalReportRead, status_code=status.HTTP_201_CREATED)
    def create_medical_report(
        payload: MedicalReportCreate,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin, UserRole.vet)),
        db: Session = Depends(get_db),
    ) -> MedicalReport:
        animal = animal_or_404(db, payload.animal_id, current_user=current_user)
        if payload.task_id is not None:
            task = vet_task_or_404(db, payload.task_id, current_user=current_user)
            if task.animal_id != payload.animal_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task belongs to another animal")
            task.status = VetTaskStatus.done
        report = MedicalReport(**payload.model_dump(), vet_user_id=current_user.id)
        # A medical report reflects a finding, so it may escalate the health status, but it
        # must never silently de-escalate (e.g. a `critical` animal must not drop to
        # `observation` just because this report needs no follow-up). Vets can still lower
        # the status deliberately via the dedicated animal-update endpoint.
        target_status = HealthStatus.treatment if payload.follow_up_required else HealthStatus.observation
        if HEALTH_SEVERITY[target_status] >= HEALTH_SEVERITY[animal.health_status]:
            animal.health_status = target_status
        db.add(report)
        db.flush()
        write_audit_log(db, current_user, "create", "medical_report", report.id, {"animal_id": report.animal_id})
        db.commit()
        db.refresh(report)
        return report

    @app.get("/public/map", response_model=PublicZooMapRead)
    def public_zoo_map(
        _rate_limit: None = Depends(enforce_public_rate_limit),
        db: Session = Depends(get_db),
    ) -> dict[str, object]:
        enclosures = (
            db.query(Enclosure)
            .options(joinedload(Enclosure.animals).joinedload(Animal.species))
            .filter(Enclosure.is_public_visible.is_(True))
            .order_by(Enclosure.name.asc())
            .all()
        )
        public_names = {enclosure.id: enclosure.public_name or enclosure.name for enclosure in enclosures}
        enclosure_payload = []
        for enclosure in enclosures:
            enclosure_payload.append(
                {
                    "public_name": public_names[enclosure.id],
                    "public_description": enclosure.public_description,
                    "location": enclosure.location,
                    "map_x": enclosure.map_x if enclosure.map_x is not None else 0,
                    "map_y": enclosure.map_y if enclosure.map_y is not None else 0,
                    "map_width": enclosure.map_width if enclosure.map_width is not None else 120,
                    "map_height": enclosure.map_height if enclosure.map_height is not None else 80,
                    "animals": [
                        {
                            "name": animal.name,
                            "species": animal.species.common_name,
                            "sex": animal.sex,
                            "age_years": animal.age_years,
                        }
                        for animal in enclosure.animals
                        if animal.active
                    ],
                }
            )
        paths = (
            db.query(MapPath)
            .filter(MapPath.from_enclosure_id.in_(public_names), MapPath.to_enclosure_id.in_(public_names))
            .all()
        )
        return {
            "enclosures": enclosure_payload,
            "paths": [
                {
                    "from_enclosure": public_names[path.from_enclosure_id],
                    "to_enclosure": public_names[path.to_enclosure_id],
                    "distance_meters": path.distance_meters,
                    "walking_time_minutes": path.walking_time_minutes,
                    "path_svg_data": path.path_svg_data,
                }
                for path in paths
            ],
        }

    @app.get("/admin/economy", response_model=EconomySummary)
    def economy_summary(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> EconomySummary:
        today = date.today()
        week_start = today - timedelta(days=6)
        visitor_stats = (
            db.query(VisitorStat)
            .filter(VisitorStat.date >= week_start)
            .order_by(VisitorStat.date.asc())
            .all()
        )
        visitors_today = sum(item.visitor_count for item in visitor_stats if item.date == today)
        visitors_week = sum(item.visitor_count for item in visitor_stats)
        ticket_revenue_week = sum(item.ticket_revenue for item in visitor_stats)
        payroll = sum(
            (
                profile.monthly_base_salary
                if profile.monthly_base_salary is not None
                else profile.hourly_rate * 160
            )
            for profile in db.query(SalaryProfile).filter(SalaryProfile.active.is_(True)).all()
        )
        food_value = sum(item.cost_per_unit * item.available_quantity for item in db.query(FoodItem).all())
        open_tasks = (
            db.query(Task).filter(Task.status != TaskStatus.done).count()
            + db.query(CareTask).filter(CareTask.status != CareTaskStatus.done).count()
        )
        open_vet_cases = db.query(VetTask).filter(VetTask.status == VetTaskStatus.open).count()
        return EconomySummary(
            visitors_today=visitors_today,
            visitors_week=visitors_week,
            ticket_revenue_week=ticket_revenue_week,
            estimated_payroll_month=payroll,
            food_inventory_value=food_value,
            open_tasks=open_tasks,
            open_vet_cases=open_vet_cases,
            visitor_stats=visitor_stats,
        )

    @app.post("/admin/salary-simulation", response_model=SalarySimulationResponse)
    def salary_simulation(
        payload: SalarySimulationRequest,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> SalarySimulationResponse:
        user = user_or_404(db, payload.user_id)
        profile = db.query(SalaryProfile).filter(SalaryProfile.user_id == user.id, SalaryProfile.active.is_(True)).first()
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary profile not found")
        start_dt = datetime.combine(payload.start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(payload.end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        sessions = (
            db.query(WorkSession)
            .filter(WorkSession.user_id == user.id, WorkSession.login_at >= start_dt, WorkSession.login_at < end_dt)
            .all()
        )
        minutes = sum(session.duration_minutes or 0 for session in sessions)
        hours = round(minutes / 60, 2)
        gross_pay = int(round(hours * profile.hourly_rate))
        tax_rate_percent = profile.tax_rate_percent if profile.tax_rate_percent is not None else 20
        estimated_deductions = int(round(gross_pay * (tax_rate_percent / 100)))
        return SalarySimulationResponse(
            user=user,
            hours=hours,
            hourly_rate=profile.hourly_rate,
            gross_pay=gross_pay,
            estimated_deductions=estimated_deductions,
            estimated_net=gross_pay - estimated_deductions,
        )

    @app.post("/admin/feeding-optimization", response_model=FeedingOptimizationResponse)
    def feeding_optimization(
        payload: FeedingOptimizationRequest,
        _csrf: None = Depends(require_csrf),
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
    ) -> FeedingOptimizationResponse:
        animal = animal_or_404(db, payload.animal_id, eager_load=True)
        requirement = (
            db.query(AnimalNutritionRequirement)
            .filter(AnimalNutritionRequirement.species_id == animal.species_id)
            .first()
        )
        food_items = (
            db.query(FoodItem)
            .filter(
                FoodItem.available_quantity > 0,
                or_(FoodItem.calories_per_unit > 0, FoodItem.protein_per_unit > 0),
            )
            .all()
        )
        if requirement is None or not food_items:
            return FeedingOptimizationResponse(
                success=False,
                message="Keine passenden Futterdaten oder Naehrstoffbedarfe vorhanden.",
                method="greedy_constraint_solver",
            )

        calories_remaining = requirement.min_calories
        protein_remaining = requirement.min_protein
        fat_total = 0
        selected: list[FeedingOptimizationItem] = []
        sorted_foods = sorted(
            food_items,
            key=lambda item: item.cost_per_unit
            / max((item.calories_per_unit / max(requirement.min_calories, 1)) + (item.protein_per_unit / max(requirement.min_protein, 1)), 0.01),
        )
        for item in sorted_foods:
            if calories_remaining <= 0 and protein_remaining <= 0:
                break
            calories_units = math.ceil(max(calories_remaining, 0) / max(item.calories_per_unit, 1))
            protein_units = math.ceil(max(protein_remaining, 0) / max(item.protein_per_unit, 1))
            quantity = min(max(calories_units, protein_units, 1), item.available_quantity)
            if requirement.max_fat is not None and item.fat_per_unit is not None:
                quantity = min(quantity, max((requirement.max_fat - fat_total) // max(item.fat_per_unit, 1), 0))
            if quantity <= 0:
                continue
            calories_remaining -= quantity * item.calories_per_unit
            protein_remaining -= quantity * item.protein_per_unit
            fat_total += quantity * (item.fat_per_unit or 0)
            selected.append(
                FeedingOptimizationItem(
                    food_item_id=item.id,
                    food_name=item.name,
                    quantity=quantity,
                    unit=item.unit,
                    cost=quantity * item.cost_per_unit,
                )
            )

        success = calories_remaining <= 0 and protein_remaining <= 0
        return FeedingOptimizationResponse(
            success=success,
            message="Optimierung erfolgreich." if success else "Optimierung nicht moeglich: Bedarfe werden nicht vollstaendig erfuellt.",
            total_cost=sum(item.cost for item in selected),
            feeding_plan=selected,
            method="greedy_constraint_solver",
        )

    @app.get("/audit-logs", response_model=list[AuditLogRead])
    def list_audit_logs(
        current_user: User = Depends(require_roles(UserRole.admin)),
        db: Session = Depends(get_db),
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=MAX_PAGE_LIMIT),
    ) -> Sequence[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return app


def assignment_role_for_user(user: User) -> AssignmentRoleType | None:
    if user.role == UserRole.keeper:
        return AssignmentRoleType.keeper
    if user.role == UserRole.vet:
        return AssignmentRoleType.vet
    return None


def assignment_filter_for_user(user: User):
    assignment_role = assignment_role_for_user(user)
    if assignment_role is None:
        return Animal.id == -1
    return Animal.assignments.any(
        and_(
            AnimalAssignment.user_id == user.id,
            AnimalAssignment.role_type == assignment_role,
            AnimalAssignment.active.is_(True),
        )
    )


def animals_for_user(db: Session, user: User):
    query = db.query(Animal).filter(Animal.active.is_(True))
    if user.role == UserRole.admin:
        return query
    if user.role in {UserRole.keeper, UserRole.vet}:
        return query.filter(assignment_filter_for_user(user))
    return query.filter(Animal.id == -1)


def enclosures_for_user(db: Session, user: User):
    query = db.query(Enclosure)
    if user.role == UserRole.admin:
        return query
    if user.role in {UserRole.keeper, UserRole.vet}:
        return query.filter(
            or_(
                Enclosure.assignments.any(
                    and_(
                        EnclosureAssignment.user_id == user.id,
                        EnclosureAssignment.active.is_(True),
                    )
                ),
                Enclosure.animals.any(assignment_filter_for_user(user)),
            )
        )
    return query.filter(Enclosure.id == -1)


def feeding_schedules_for_user(db: Session, user: User):
    query = db.query(FeedingSchedule).join(FeedingSchedule.animal).filter(Animal.active.is_(True))
    if user.role == UserRole.admin:
        return query
    if user.role in {UserRole.keeper, UserRole.vet}:
        return query.filter(assignment_filter_for_user(user))
    return query.filter(FeedingSchedule.id == -1)


def health_records_for_user(db: Session, user: User):
    query = db.query(HealthRecord).join(HealthRecord.animal).filter(Animal.active.is_(True))
    if user.role == UserRole.admin:
        return query
    if user.role == UserRole.vet:
        return query.filter(assignment_filter_for_user(user))
    return query.filter(HealthRecord.id == -1)


def tasks_for_user(db: Session, user: User):
    query = db.query(Task)
    if user.role == UserRole.admin:
        return query
    if user.role in {UserRole.keeper, UserRole.vet}:
        return query.filter(Task.assigned_role == user.role)
    return query.filter(Task.id == -1)


def care_tasks_for_user(db: Session, user: User):
    query = db.query(CareTask)
    if user.role == UserRole.admin:
        return query
    return query.filter(CareTask.assigned_to_user_id == user.id)


def vet_tasks_for_user(db: Session, user: User):
    query = db.query(VetTask)
    if user.role == UserRole.admin:
        return query
    return query.filter(VetTask.assigned_to_user_id == user.id)


def user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def animal_or_404(
    db: Session,
    animal_id: int,
    *,
    current_user: User | None = None,
    eager_load: bool = False,
) -> Animal:
    query = db.query(Animal).filter(Animal.id == animal_id, Animal.active.is_(True))
    if current_user is not None and current_user.role != UserRole.admin:
        query = query.filter(assignment_filter_for_user(current_user))
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


def feeding_schedule_or_404(db: Session, schedule_id: int, *, current_user: User | None = None) -> FeedingSchedule:
    query = feeding_schedules_for_user(db, current_user) if current_user is not None else db.query(FeedingSchedule)
    schedule = query.filter(FeedingSchedule.id == schedule_id).first()
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeding schedule not found")
    return schedule


def health_record_or_404(db: Session, record_id: int, *, current_user: User | None = None) -> HealthRecord:
    query = health_records_for_user(db, current_user) if current_user is not None else db.query(HealthRecord)
    record = query.filter(HealthRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found")
    return record


def task_or_404(db: Session, task_id: int, *, current_user: User | None = None) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user is not None and current_user.role != UserRole.admin and task.assigned_role != current_user.role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def care_task_or_404(db: Session, task_id: int, *, current_user: User | None = None) -> CareTask:
    task = db.get(CareTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care task not found")
    if current_user is not None and current_user.role != UserRole.admin and task.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care task not found")
    return task


def vet_task_or_404(db: Session, task_id: int, *, current_user: User | None = None) -> VetTask:
    task = db.get(VetTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vet task not found")
    if current_user is not None and current_user.role != UserRole.admin and task.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vet task not found")
    return task


def assigned_vet_for_animal(db: Session, animal_id: int) -> User | None:
    # Only an explicitly assigned, active vet is returned. There is deliberately no
    # "first available vet" fallback: silently overloading an arbitrary vet hides the
    # fact that an animal lacks proper veterinary coverage.
    assignment = (
        db.query(AnimalAssignment)
        .join(AnimalAssignment.user)
        .filter(
            AnimalAssignment.animal_id == animal_id,
            AnimalAssignment.role_type == AssignmentRoleType.vet,
            AnimalAssignment.active.is_(True),
            User.is_active.is_(True),
        )
        .order_by(AnimalAssignment.created_at.asc())
        .first()
    )
    return assignment.user if assignment is not None else None


def ensure_species_and_enclosure(db: Session, species_id: int, enclosure_id: int) -> None:
    species_or_404(db, species_id)
    enclosure_or_404(db, enclosure_id)


app = create_app()
