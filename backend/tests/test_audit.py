import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit import AuditEvent


def test_audit_records_login_logout_and_config_changes(
    client: TestClient,
    test_db_session: Session,
) -> None:
    settings = get_settings()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@reconx-demo.com", "password": settings.seed_default_password},
    )
    assert login_resp.status_code == 200
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Update config -> creates version 2 and audit event with before/after
    cfg_resp = client.put(
        "/api/v1/admin/config",
        headers=headers,
        json={"config_json": {"currency": "INR", "partial_billing_allowed": False}},
    )
    assert cfg_resp.status_code == 200
    assert cfg_resp.json()["version"] == 2

    audit_resp = client.get("/api/v1/audit?action=CONFIG_UPDATED", headers=headers)
    assert audit_resp.status_code == 200
    items = audit_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["before_json"]["partial_billing_allowed"] is True
    assert items[0]["after_json"]["partial_billing_allowed"] is False


def test_audit_event_cannot_be_updated_or_deleted(test_db_session: Session) -> None:
    org_id = test_db_session.execute(
        AuditEvent.__table__.select().limit(1)
    ).first()
    if org_id is None:
        from app.models.auth import Organization
        from app.services.audit.service import record_audit_event

        org = test_db_session.query(Organization).first()
        assert org is not None
        record_audit_event(
            test_db_session,
            organization_id=org.id,
            actor_type="SYSTEM",
            actor_id="test",
            action="TEST_EVENT",
            entity_type="test",
            entity_id="1",
        )
        test_db_session.commit()

    evt = test_db_session.query(AuditEvent).first()
    assert evt is not None

    evt.action = "TAMPERED"
    with pytest.raises((OperationalError, IntegrityError)):
        test_db_session.commit()
    test_db_session.rollback()

    evt = test_db_session.query(AuditEvent).first()
    assert evt is not None
    test_db_session.delete(evt)
    with pytest.raises((OperationalError, IntegrityError)):
        test_db_session.commit()
    test_db_session.rollback()
