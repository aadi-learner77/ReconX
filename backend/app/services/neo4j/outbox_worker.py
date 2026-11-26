from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import asc, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.policy import GraphOutboxEvent
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.repository import Neo4jUnavailableError
from app.services.neo4j.schema import ensure_neo4j_schema
from app.services.neo4j.sync_service import sync_investigation_to_neo4j, sync_transaction_to_neo4j


def process_pending_outbox_events(
    db: Session,
    *,
    organization_id: UUID | None = None,
    batch_size: int | None = None,
) -> dict[str, Any]:
    """Consume PENDING graph_outbox_event rows and apply idempotent Neo4j projections."""
    settings = get_settings()
    if not neo4j_manager.is_enabled():
        return {"processed": 0, "failed": 0, "skipped": True, "reason": "GRAPH_BACKEND!=neo4j"}

    ok, detail = neo4j_manager.verify_connectivity()
    if not ok:
        return {"processed": 0, "failed": 0, "skipped": True, "reason": detail}

    if not neo4j_manager.schema_initialized:
        ensure_neo4j_schema()

    limit = batch_size or settings.graph_sync_batch_size
    stmt = (
        select(GraphOutboxEvent)
        .where(GraphOutboxEvent.status == "PENDING")
        .order_by(asc(GraphOutboxEvent.created_at))
        .limit(limit)
    )
    if organization_id is not None:
        stmt = stmt.where(GraphOutboxEvent.organization_id == organization_id)

    events = list(db.scalars(stmt).all())
    processed = 0
    failed = 0
    for evt in events:
        try:
            evt.attempts += 1
            if evt.entity_type == "investigation":
                sync_investigation_to_neo4j(
                    db,
                    organization_id=evt.organization_id,
                    investigation_id=UUID(evt.entity_id),
                )
            else:
                tx_id_raw = (evt.payload_json or {}).get("transaction_id") or evt.entity_id
                sync_transaction_to_neo4j(
                    db,
                    organization_id=evt.organization_id,
                    transaction_id=UUID(str(tx_id_raw)),
                )
            evt.status = "PROCESSED"
            evt.last_error = None
            evt.last_error_category = None
            evt.processed_at = datetime.now(UTC)
            processed += 1
        except (Neo4jUnavailableError, Exception) as exc:
            evt.last_error_category = type(exc).__name__
            evt.last_error = str(exc)[:500]
            if evt.attempts >= settings.graph_sync_retry_limit:
                evt.status = "FAILED"
                failed += 1
    db.commit()
    return {"processed": processed, "failed": failed, "skipped": False}


def retry_failed_outbox_events(db: Session, *, organization_id: UUID) -> dict[str, Any]:
    db.execute(
        update(GraphOutboxEvent)
        .where(
            GraphOutboxEvent.organization_id == organization_id,
            GraphOutboxEvent.status == "FAILED",
        )
        .values(status="PENDING", attempts=0, last_error=None, last_error_category=None)
    )
    db.commit()
    return process_pending_outbox_events(db, organization_id=organization_id)
