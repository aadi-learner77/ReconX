from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import Organization
from app.models.domain import Invoice, PurchaseOrder, Vendor
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_orchestrated_investigation_trace_and_graph_rebuild(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    headers = _login_headers(client, "operator@reconx-demo.com")
    auditor_headers = _login_headers(client, "auditor@reconx-demo.com")

    tx2 = client.get(
        "/api/v1/transactions?scenario_label=AT-02", headers=headers
    ).json()["items"][0]
    tx_id = tx2["transaction_id"]
    client.post(f"/api/v1/transactions/{tx_id}/reconcile", headers=headers)
    exc = client.get(
        f"/api/v1/exceptions?transaction_id={tx_id}", headers=headers
    ).json()["items"][0]

    inv = client.post(f"/api/v1/exceptions/{exc['id']}/investigations", headers=headers)
    assert inv.status_code == 201
    data = inv.json()
    agents_ran = [s["agent"] for s in data["execution_trace"]]
    assert agents_ran == [
        "DocumentAgent",
        "MatchingAgent",
        "RiskAgent",
        "VendorIntelligenceAgent",
        "EvidenceGraphAgent",
        "InvestigationAgent",
        "AuditAgent",
    ]
    assert data["human_approval_required"] is True

    # Graph includes Investigation + HistoricalPO + rebuild endpoint audits
    graph = client.get(f"/api/v1/graph/transactions/{tx_id}?include_history=true", headers=headers)
    assert graph.status_code == 200
    node_types = {n["type"] for n in graph.json()["nodes"]}
    assert "Investigation" in node_types

    rebuilt = client.post(f"/api/v1/graph/transactions/{tx_id}/rebuild", headers=headers)
    assert rebuilt.status_code == 200
    audit = client.get("/api/v1/audit?action=GRAPH_REBUILT", headers=auditor_headers)
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1


def test_split_invoice_shared_bank_and_cash_forecast(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    headers = _login_headers(client, "operator@reconx-demo.com")

    org = test_db_session.query(Organization).first()
    assert org is not None
    v1 = Vendor(
        organization_id=org.id,
        legal_name="Split Supply Co",
        normalized_name="splitsupplyco",
        bank_account_masked="ACCT-SHARED-7788",
    )
    v2 = Vendor(
        organization_id=org.id,
        legal_name="Shell Sibling Co",
        normalized_name="shellsiblingco",
        bank_account_masked="ACCT-SHARED-7788",
    )
    test_db_session.add_all([v1, v2])
    test_db_session.flush()

    po = PurchaseOrder(
        organization_id=org.id,
        vendor_id=v1.id,
        po_number="PO-SPLIT-9001",
        issue_date=date(2026, 10, 1),
        currency="INR",
        total_amount=Decimal("10000.0000"),
    )
    test_db_session.add(po)
    test_db_session.flush()

    inv1 = Invoice(
        organization_id=org.id,
        vendor_id=v1.id,
        po_id=po.id,
        invoice_number="INV-SPL-1",
        normalized_invoice_number="INVSPL1",
        invoice_date=date(2026, 10, 2),
        due_date=date(2026, 11, 1),
        currency="INR",
        tax_amount=Decimal("0.0000"),
        total_amount=Decimal("5000.0000"),
    )
    inv2 = Invoice(
        organization_id=org.id,
        vendor_id=v1.id,
        po_id=po.id,
        invoice_number="INV-SPL-2",
        normalized_invoice_number="INVSPL2",
        invoice_date=date(2026, 10, 4),
        due_date=date(2026, 11, 3),
        currency="INR",
        tax_amount=Decimal("0.0000"),
        total_amount=Decimal("4800.0000"),
    )
    test_db_session.add_all([inv1, inv2])
    test_db_session.commit()

    risk_resp = client.get(f"/api/v1/transactions/{po.id}/risk", headers=headers)
    assert risk_resp.status_code == 200
    sig_types = {s["signal_type"] for s in risk_resp.json()["signals"]}
    assert "SPLIT_INVOICE_PATTERN" in sig_types
    assert "SHARED_BANK_ACCOUNT" in sig_types

    cash_resp = client.get("/api/v1/analytics/cash-obligations", headers=headers)
    assert cash_resp.status_code == 200
    cdata = cash_resp.json()
    assert len(cdata["forecast_30_60_90"]) == 3
    assert "forecast_methodology" in cdata


def test_upgraded_copilot_structured_tools_and_guardrails(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    headers = _login_headers(client, "operator@reconx-demo.com")

    # Lookup by PO number
    r_po = client.post(
        "/api/v1/copilot/query",
        headers=headers,
        json={"question": "Show status of PO-2026-0001"},
    )
    assert r_po.status_code == 200
    assert r_po.json()["tool_used"] == "query_transaction_by_ref"
    assert "PO-2026-0001" in r_po.json()["answer"]

    # Cash forecast query
    r_cash = client.post(
        "/api/v1/copilot/query",
        headers=headers,
        json={"question": "What is our cash forecast and overdue total?"},
    )
    assert r_cash.status_code == 200
    assert r_cash.json()["tool_used"] == "query_cash_forecast"

    # Write guardrail still blocks
    r_write = client.post(
        "/api/v1/copilot/query",
        headers=headers,
        json={"question": "approve PO-2026-0001 now"},
    )
    assert r_write.status_code == 200
    assert r_write.json()["tool_used"] == "write_guardrail"
    assert r_write.json()["read_only"] is True


def test_agent_harness_and_obligation_graph_endpoints(
    client: TestClient, test_db_session: Session, monkeypatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    seed_synthetic_dataset(test_db_session, reset=True)
    headers = _login_headers(client, "operator@reconx-demo.com")

    tx2 = client.get(
        "/api/v1/transactions?scenario_label=AT-02", headers=headers
    ).json()["items"][0]
    tx2_id = tx2["transaction_id"]
    client.post(f"/api/v1/transactions/{tx2_id}/reconcile", headers=headers)
    exc_id = client.get(
        f"/api/v1/exceptions?transaction_id={tx2_id}", headers=headers
    ).json()["items"][0]["id"]
    client.post(f"/api/v1/exceptions/{exc_id}/investigations", headers=headers)

    harness = client.get("/api/v1/intelligence/agent-harness", headers=headers)
    assert harness.status_code == 200
    hdata = harness.json()
    assert [a["id"] for a in hdata["configured_agents"]] == [
        "DocumentAgent",
        "MatchingAgent",
        "RiskAgent",
        "VendorIntelligenceAgent",
        "EvidenceGraphAgent",
        "InvestigationAgent",
        "AuditAgent",
    ]
    assert len(hdata["harness_components"]) == 8
    assert hdata["system_status"]["active_provider"] == "mock"
    assert len(hdata["recent_traces"]) >= 1
    assert hdata["recent_traces"][0]["model_provider"] == "mock"

    ob = client.get(f"/api/v1/graph/obligations/{tx2_id}", headers=headers)
    assert ob.status_code == 200
    odata = ob.json()
    assert odata["has_payment_records"] is False
    assert all(e["label"] != "SETTLES" for e in odata["edges"])
    assert Decimal(odata["summary"]["ordered_qty"]) == Decimal("100")
    assert Decimal(odata["summary"]["accepted_qty"]) == Decimal("90")
    assert Decimal(odata["summary"]["unsupported_invoiced_qty"]) == Decimal("10")
    edge_labels = {e["label"] for e in odata["edges"]}
    assert "RECEIVES_ORDER" in edge_labels
    assert "CREATES" in edge_labels
    assert "FULFILLS" in edge_labels
    assert "BILLS_AGAINST" in edge_labels
