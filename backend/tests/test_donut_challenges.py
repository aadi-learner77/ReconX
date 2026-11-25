from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import Organization
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_donut1_policy_dsl_validation_and_rbac(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    op = _login_headers(client, "operator@reconx-demo.com")
    admin = _login_headers(client, "admin@reconx-demo.com")

    # Operator cannot create policy (403)
    r_forbid = client.post(
        "/api/v1/policies",
        headers=op,
        json={
            "policy_key": "POL-OP-1",
            "name": "Unauthorized",
            "category": "FINANCIAL",
            "severity": "HIGH",
            "definition": {
                "condition": {"field": "variance.qty_diff", "operator": "gt", "value": "5"}
            },
        },
    )
    assert r_forbid.status_code == 403

    # Reject unknown field
    r_bad_field = client.post(
        "/api/v1/policies",
        headers=admin,
        json={
            "policy_key": "POL-BAD-1",
            "name": "Bad Field",
            "category": "FINANCIAL",
            "severity": "HIGH",
            "definition": {
                "condition": {"field": "user.password_hash", "operator": "eq", "value": "x"}
            },
        },
    )
    assert r_bad_field.status_code == 422

    # Reject unsupported operator / eval injection
    r_bad_op = client.post(
        "/api/v1/policies",
        headers=admin,
        json={
            "policy_key": "POL-BAD-2",
            "name": "Bad Op",
            "category": "FINANCIAL",
            "severity": "HIGH",
            "definition": {
                "condition": {"field": "variance.qty_diff", "operator": "eval", "value": "1+1"}
            },
        },
    )
    assert r_bad_op.status_code == 422


def test_donut1_policy_hotswap_preview_reaudit_and_idempotency(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    admin = _login_headers(client, "admin@reconx-demo.com")

    # Dry-run impact preview before creating/activating
    prev = client.post(
        "/api/v1/policies/preview",
        headers=admin,
        json={
            "policy_key": "POL-LIVE-QTY",
            "severity": "HIGH",
            "definition": {
                "condition": {"field": "variance.qty_diff", "operator": "gt", "value": "5"}
            },
        },
    )
    assert prev.status_code == 200
    pdata = prev.json()
    assert pdata["dry_run"] is True
    assert pdata["records_scanned"] >= 10
    assert pdata["records_matching"] >= 1

    # Create and activate policy without restart
    created = client.post(
        "/api/v1/policies",
        headers=admin,
        json={
            "policy_key": "POL-LIVE-QTY",
            "name": "Live Quantity Variance > 5",
            "description": "Flags qty_diff > 5",
            "category": "FINANCIAL",
            "severity": "HIGH",
            "definition": {
                "condition": {"field": "variance.qty_diff", "operator": "gt", "value": "5"}
            },
        },
    )
    assert created.status_code == 201
    pol_id = created.json()["id"]

    act = client.post(f"/api/v1/policies/{pol_id}/activate", headers=admin)
    assert act.status_code == 200
    assert act.json()["status"] == "ACTIVE"
    assert act.json()["active_version"] == 1

    # Re-Run Audit -> creates new exceptions
    run1 = client.post("/api/v1/policy-audits", headers=admin, json={"policy_ids": [pol_id]})
    assert run1.status_code == 201
    r1 = run1.json()
    assert r1["status"] == "SUCCEEDED"
    assert r1["new_exceptions"] >= 1

    # Re-Run Audit again -> idempotent (0 new exceptions, counted as existing)
    run2 = client.post("/api/v1/policy-audits", headers=admin, json={"policy_ids": [pol_id]})
    assert run2.status_code == 201
    r2 = run2.json()
    assert r2["new_exceptions"] == 0
    assert r2["existing_exceptions"] >= 1

    # Edit policy -> creates immutable v2
    upd = client.put(
        f"/api/v1/policies/{pol_id}",
        headers=admin,
        json={
            "definition": {
                "condition": {"field": "variance.qty_diff", "operator": "gt", "value": "500"}
            },
            "change_summary": "Raised threshold to 500",
        },
    )
    assert upd.status_code == 200
    assert upd.json()["latest_version"] == 2
    vers = client.get(f"/api/v1/policies/{pol_id}/versions", headers=admin).json()
    assert len(vers) == 2

    # Activate v2 and re-audit -> previously flagged conditions no longer triggered
    client.post(f"/api/v1/policies/{pol_id}/activate", headers=admin)
    run3 = client.post("/api/v1/policy-audits", headers=admin, json={"policy_ids": [pol_id]})
    assert run3.status_code == 201
    assert run3.json()["resolved_exceptions"] >= 1


def test_donut2_executive_brief_citations_exports_and_isolation(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    admin = _login_headers(client, "admin@reconx-demo.com")
    op = _login_headers(client, "operator@reconx-demo.com")

    # Reconcile AT-02 so an open exception with exact Decimal exposure exists
    tx2 = client.get(
        "/api/v1/transactions?scenario_label=AT-02", headers=op
    ).json()["items"][0]
    client.post(f"/api/v1/transactions/{tx2['transaction_id']}/reconcile", headers=op)

    audit_run = client.post("/api/v1/policy-audits", headers=admin, json={}).json()

    brief_resp = client.post(
        "/api/v1/executive-briefs",
        headers=admin,
        json={"scope": "POLICY_AUDIT_RUN", "policy_audit_run_id": audit_run["id"]},
    )
    assert brief_resp.status_code == 201
    brief = brief_resp.json()
    assert brief["metrics"]["total_open_exceptions"] >= 1
    assert len(brief["top_exceptions"]) >= 1
    assert len(brief["citations"]) >= 1
    assert brief["policy_diff"]["audit_run_id"] == audit_run["id"]

    # PDF, Markdown, CSV downloads
    pdf = client.get(
        f"/api/v1/executive-briefs/{brief['id']}/download?format=pdf", headers=admin
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")

    md = client.get(
        f"/api/v1/executive-briefs/{brief['id']}/download?format=markdown", headers=admin
    )
    assert md.status_code == 200
    assert b"ReconX AI" in md.content

    csv_r = client.get(
        f"/api/v1/executive-briefs/{brief['id']}/download?format=csv", headers=admin
    )
    assert csv_r.status_code == 200
    assert b"EXECUTIVE_METRICS" in csv_r.content

    # Cross-tenant isolation check
    other_org = Organization(
        name="Org Isolation Test", base_currency="USD", timezone="UTC", settings_json={}
    )
    test_db_session.add(other_org)
    test_db_session.commit()
    briefs_list = client.get("/api/v1/executive-briefs", headers=admin).json()
    assert brief["id"] in [b["id"] for b in briefs_list]
