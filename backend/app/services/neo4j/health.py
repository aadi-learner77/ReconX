from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.policy import GraphOutboxEvent
from app.repositories.base import OrgScopedRepository
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.repository import Neo4jUnavailableError, run_read


def get_sync_status(db: Session, organization_id: UUID) -> dict[str, Any]:
    repo = OrgScopedRepository(db, GraphOutboxEvent, organization_id)
    pending = (
        db.scalar(
            select(func.count()).select_from(
                repo.base_query().where(GraphOutboxEvent.status == "PENDING").subquery()
            )
        )
        or 0
    )
    failed = (
        db.scalar(
            select(func.count()).select_from(
                repo.base_query().where(GraphOutboxEvent.status == "FAILED").subquery()
            )
        )
        or 0
    )
    processed = (
        db.scalar(
            select(func.count()).select_from(
                repo.base_query().where(GraphOutboxEvent.status == "PROCESSED").subquery()
            )
        )
        or 0
    )
    last_ok = db.scalar(
        repo.base_query()
        .where(GraphOutboxEvent.status == "PROCESSED")
        .order_by(desc(GraphOutboxEvent.processed_at))
        .limit(1)
    )

    driver_snap = neo4j_manager.status_snapshot()
    nodes_synced = 0
    rels_synced = 0
    if driver_snap["connected"]:
        try:
            n_rows = run_read(
                "MATCH (n {organization_id: $org_id}) RETURN count(n) AS cnt",
                {"org_id": str(organization_id)},
            )
            r_rows = run_read(
                "MATCH (a {organization_id: $org_id})-[r]->(b {organization_id: $org_id}) "
                "RETURN count(r) AS cnt",
                {"org_id": str(organization_id)},
            )
            nodes_synced = int(n_rows[0]["cnt"]) if n_rows else 0
            rels_synced = int(r_rows[0]["cnt"]) if r_rows else 0
        except Neo4jUnavailableError:
            driver_snap["connected"] = False

    if not driver_snap["enabled"]:
        sync_state = "RELATIONAL_MODE"
    elif not driver_snap["connected"]:
        sync_state = "DEGRADED"
    elif failed > 0 or pending > 0:
        sync_state = "STALE"
    elif nodes_synced == 0 and processed == 0:
        sync_state = "NEEDS_BACKFILL"
    else:
        sync_state = "CURRENT"

    return {
        "neo4j_enabled": driver_snap["enabled"],
        "neo4j_connected": driver_snap["connected"],
        "graph_backend": driver_snap["graph_backend"],
        "database": driver_snap["database"],
        "sync_state": sync_state,
        "stale": sync_state in ("STALE", "DEGRADED", "NEEDS_BACKFILL"),
        "pending_events": int(pending),
        "failed_events": int(failed),
        "processed_events": int(processed),
        "nodes_synchronized": nodes_synced,
        "relationships_synchronized": rels_synced,
        "last_successful_sync": (
            last_ok.processed_at.isoformat() if last_ok and last_ok.processed_at else None
        ),
        "detail": driver_snap["detail"],
    }


def get_graph_health(db: Session, organization_id: UUID) -> dict[str, Any]:
    return get_sync_status(db, organization_id)
