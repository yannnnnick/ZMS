from __future__ import annotations

import os
from collections.abc import Generator
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zoo.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# SQLite ignores server-side pool tuning, so only apply pool settings for real
# client/server databases (e.g. PostgreSQL) where connection churn and stale
# connections are a genuine concern under load.
engine_kwargs: dict[str, object] = {"connect_args": connect_args}
if not _is_sqlite:
    engine_kwargs.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE_SECONDS", "3600")),
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

if DATABASE_URL.startswith("sqlite"):
    logger.warning("SQLite is intended for local development only; use PostgreSQL for production deployments.")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Any exception escaping a request handler (HTTPException or otherwise) is
        # thrown back into this generator by FastAPI's dependency machinery. Rolling
        # back here guarantees no half-applied write transaction is left hanging,
        # removing the need for per-endpoint try/except/rollback blocks.
        db.rollback()
        raise
    finally:
        db.close()


def init_db(seed: bool = True) -> None:
    from . import models
    from .seed import seed_demo_data

    models.Base.metadata.create_all(bind=engine)
    if seed:
        seed_demo_data(SessionLocal)
