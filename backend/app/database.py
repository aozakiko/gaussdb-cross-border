"""Database session helpers."""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()
DATABASE_URL = settings.get_database_url()

engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,
    future=True,
)


def _force_pg_version(*_args, **_kwargs):
    return (12, 0)


engine.dialect.server_version_info = (12, 0)
engine.dialect.postgresql_version = 120000
engine.dialect._get_server_version_info = _force_pg_version
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db() -> Iterator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def override_db(url: str) -> Iterator[None]:
    """Used mainly in tests to temporarily point to another database."""

    global engine, SessionLocal
    old_engine = engine
    old_session = SessionLocal
    try:
        engine = create_engine(url, pool_pre_ping=True, future=True)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
        yield
    finally:
        engine.dispose()
        engine = old_engine
        SessionLocal = old_session
