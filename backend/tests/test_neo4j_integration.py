from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.policy import GraphOutboxEvent
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.outbox_worker import process_pending_outbox_events, retry_failed_outbox_events
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_graph_outbox_and_graceful_fallback_when_neo4j_disabled(
    client: TestClient, test_db_session: Session, monkeypatch
) -> None:
    monkeypatch.setenv("GRAPH_BACKEND", "relational")
    get_settings.cache_clear()
    neo4j_manager.close()

    seed_synthetic_dataset(test_db_session, reset=True)
    op_headers = _login_headers(client, "operator@reconx-demo.com")
    admin_headers = _login_headers(client, "admin@reconx-demo.com")

    # Health & sync status work in relational fallback mode
    h = client.get("/api/v1/graph/health", headers=op_headers)
    assert h.status_code == 200
    assert h.json()["sync_state"] == "RELATIONAL_MODE"
    assert h.json()["neo4j_connected"] is False

    # Reconcile PO-2026-0002 -> succeeds & enqueues outbox event even when Neo4j is off
    tx2 = client.get("/api/v1/transactions?scenario_label=AT-02", headers=op_headers).json()["items"][0]
    tx2_id = tx2["transaction_id"]
    rec = client.post(f"/api/v1/transactions/{tx2_id}/reconcile", headers=op_headers)
    assert rec.status_code == 200
    assert rec.json()["outcome"] == "EXCEPTION"

    outbox_rows = list(test_db_session.scalars(select(GraphOutboxEvent)).all())
    assert len(outbox_rows) >= 1
    assert outbox_rows[0].status == "PENDING"

    # Obligation graph falls back cleanly to PostgreSQL relational projection
    ob = client.get(f"/api/v1/graph/obligations/{tx2_id}?view=overview", headers=op_headers)
    assert ob.status_code == 200
    assert ob.json()["source"] == "postgresql_relational_fallback"
    assert len(ob.json()["nodes"]) >= 3

    # RBAC: operator cannot trigger admin backfill (403), admin can call endpoint safely
    assert client.post("/api/v1/graph/sync/backfill", headers=op_headers).status_code == 403
    bf = client.post("/api/v1/graph/sync/backfill", headers=admin_headers)
    assert bf.status_code == 200
    assert bf.json()["ok"] is False

    # Outbox worker skips cleanly when disabled
    res = process_pending_outbox_events(test_db_session)
    assert res["skipped"] is True

    # Retry failed endpoint works for admin
    rf = client.post("/api/v1/graph/sync/retry-failed", headers=admin_headers)
    assert rf.status_code == 200


def test_neo4j_degraded_when_unreachable_does_not_block_finance(
    client: TestClient, test_db_session: Session, monkeypatch
) -> None:
    monkeypatch.setenv("GRAPH_BACKEND", "neo4j")
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:17687")
    monkeypatch.setenv("NEO4J_PASSWORD", "wrong_pass")
    monkeypatch.setenv("GRAPH_QUERY_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()
    neo4j_manager.close()

    seed_synthetic_dataset(test_db_session, reset=True)
    op_headers = _login_headers(client, "operator@reconx-demo.com")

    h = client.get("/api/v1/graph/health", headers=op_headers)
    assert h.status_code == 200
    assert h.json()["sync_state"] == "DEGRADED"
    assert h.json()["stale"] is True

    # Core reconciliation & investigation still succeed when Neo4j is down
    tx2 = client.get("/api/v1/transactions?scenario_label=AT-02", headers=op_headers).json()["items"][0]
    tx2_id = tx2["transaction_id"]
    rec = client.post(f"/api/v1/transactions/{tx2_id}/reconcile", headers=op_headers)
    assert rec.status_code == 200

    # Agent graph & risk discovery report degraded safely
    ag = client.get("/api/v1/graph/agents/analytics", headers=op_headers)
    assert ag.status_code == 200
    assert ag.json()["degraded"] is True

    rd = client.get("/api/v1/graph/risk-discovery", headers=op_headers)
    assert rd.status_code == 200
    assert rd.json()["degraded"] is True
    assert "not proof of fraud" in rd.json()["disclaimer"].lower()

    neo4j_manager.close()
    monkeypatch.setenv("GRAPH_BACKEND", "relational")
    get_settings.cache_clear()
