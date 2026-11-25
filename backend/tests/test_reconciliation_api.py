from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _tx_id_by_scenario(client: TestClient, headers: dict[str, str], label: str) -> str:
    resp = client.get(f"/api/v1/transactions?scenario_label={label}", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1, f"Expected 1 transaction for {label}, got {len(items)}"
    return items[0]["transaction_id"]


def test_acceptance_at01_through_at06_via_api(
    client: TestClient,
    test_db_session: Session,
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    headers = _login_headers(client, "operator@reconx-demo.com")

    expected = {
        "AT-01": "MATCHED",
        "AT-02": "EXCEPTION",
        "AT-03": "MATCHED",
        "AT-04": "EXCEPTION",
        "AT-05": "EXCEPTION",
        "AT-06": "INCOMPLETE",
        "SUPPLIER_MISMATCH": "EXCEPTION",
        "TAX_VARIANCE": "EXCEPTION",
        "SPLIT_INVOICE": "MATCHED",
        "REJECTED_QUANTITY": "EXCEPTION",
        "TOLERANCE_PASS": "MATCHED_WITH_TOLERANCE",
    }

    for label, expected_outcome in expected.items():
        tx_id = _tx_id_by_scenario(client, headers, label)
        r = client.post(f"/api/v1/transactions/{tx_id}/reconcile", headers=headers)
        assert r.status_code == 200, f"{label}: {r.text}"
        body = r.json()
        assert body["outcome"] == expected_outcome, f"{label}: got {body}"

    # Verify audit events exist for reconciliation runs
    admin_headers = _login_headers(client, "auditor@reconx-demo.com")
    audit = client.get("/api/v1/audit?action=RECONCILIATION_EXECUTED", headers=admin_headers)
    assert audit.status_code == 200
    assert audit.json()["total"] == len(expected)
