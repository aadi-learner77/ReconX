from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import correlation_id_var, redact_value
from app.models.audit import AuditEvent


def record_audit_event(
    db: Session,
    *,
    organization_id: UUID,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        actor_type=actor_type,
        actor_id=str(actor_id),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_json=redact_value("before", before) if before is not None else None,
        after_json=redact_value("after", after) if after is not None else None,
        correlation_id=correlation_id or correlation_id_var.get() or "",
    )
    db.add(event)
    db.flush()
    return event
