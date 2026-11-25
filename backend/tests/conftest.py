import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure test defaults are set before importing app settings
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-chars-long")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("WORKER_ENABLED", "false")

from app.core.database import Base, ensure_sqlite_audit_triggers, get_db  # noqa: E402
from app.core.security import login_rate_limiter  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.bootstrap import seed_foundation_users  # noqa: E402


@pytest.fixture()
def test_db_session(tmp_path: Path):
    db_file = tmp_path / "test_reconx.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_audit_triggers(engine)

    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = TestingSessionLocal()
    try:
        seed_foundation_users(session)
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(test_db_session: Session):
    login_rate_limiter.reset()
    app = create_app()

    def _override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
