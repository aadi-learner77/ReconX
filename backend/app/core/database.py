from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine(database_url: str) -> Engine:
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


settings = get_settings()
engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def ensure_sqlite_audit_triggers(target_engine: Engine) -> None:
    """Install SQLite BEFORE UPDATE/DELETE triggers on audit_event for local test parity."""
    if not str(target_engine.url).startswith("sqlite"):
        return
    with target_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS prevent_audit_event_update
                BEFORE UPDATE ON audit_event
                BEGIN
                    SELECT RAISE(ABORT, 'audit_event is append-only: UPDATE forbidden');
                END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS prevent_audit_event_delete
                BEFORE DELETE ON audit_event
                BEGIN
                    SELECT RAISE(ABORT, 'audit_event is append-only: DELETE forbidden');
                END;
                """
            )
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
