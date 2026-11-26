from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.domain import Investigation, Invoice, PurchaseOrder
from app.models.policy import GraphOutboxEvent
from app.repositories.base import OrgScopedRepository
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.health import get_sync_status
from app.services.neo4j.repository import run_write
from app.services.neo4j.schema import ensure_neo4j_schema
from app.services.neo4j.sync_service import sync_investigation_to_neo4j, sync_transaction_to_neo4j


def backfill_organization_graph(db: Session, *, organization_id: UUID) -> dict[str, Any]:
    """Idempotently backfill all org-scoped PostgreSQL records into Neo4j."""
    if not neo4j_manager.is_enabled():
        return {"ok": False, "reason": "GRAPH_BACKEND is not neo4j"}
    ok, detail = neo4j_manager.verify_connectivity()
    if not ok:
        return {"ok": False, "reason": detail}

    ensure_neo4j_schema()

    po_ids = list(
        db.scalars(
            select(PurchaseOrder.id).where(PurchaseOrder.organization_id == organization_id)
        ).all()
    )
    standalone_inv_ids = list(
        db.scalars(
            select(Invoice.id).where(
                Invoice.organization_id == organization_id, Invoice.po_id.is_(None)
            )
        ).all()
    )
    inv_ids = list(
        db.scalars(
            OrgScopedRepository(db, Investigation, organization_id)
            .base_query()
            .with_only_columns(Investigation.id)
        ).all()
    )

    tx_count = 0
    for tx_id in [*po_ids, *standalone_inv_ids]:
        if sync_transaction_to_neo4j(db, organization_id=organization_id, transaction_id=tx_id):
            tx_count += 1

    agent_count = 0
    for ig_id in inv_ids:
        if sync_investigation_to_neo4j(db, organization_id=organization_id, investigation_id=ig_id):
            agent_count += 1

    db.execute(
        update(GraphOutboxEvent)
        .where(
            GraphOutboxEvent.organization_id == organization_id,
            GraphOutboxEvent.status == "PENDING",
        )
        .values(status="PROCESSED", processed_at=datetime.now(UTC))
    )
    db.commit()

    status_snap = get_sync_status(db, organization_id)
    return {
        "ok": True,
        "transactions_synced": tx_count,
        "investigations_synced": agent_count,
        **status_snap,
    }


def rebuild_organization_graph(db: Session, *, organization_id: UUID) -> dict[str, Any]:
    """Clear org-scoped nodes in Neo4j and run a clean idempotent backfill."""
    if not neo4j_manager.is_enabled():
        return {"ok": False, "reason": "GRAPH_BACKEND is not neo4j"}
    ok, detail = neo4j_manager.verify_connectivity()
    if not ok:
        return {"ok": False, "reason": detail}

    run_write(
        "MATCH (n {organization_id: $org_id}) DETACH DELETE n",
        {"org_id": str(organization_id)},
    )
    return backfill_organization_graph(db, organization_id=organization_id)
