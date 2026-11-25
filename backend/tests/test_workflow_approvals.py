from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import User
from app.models.domain import ExceptionCase
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_exception_for_scenario(
    client: TestClient, operator_headers: dict[str, str], label: str
) -> dict:
    tx_resp = client.get(f"/api/v1/transactions?scenario_label={label}", headers=operator_headers)
    tx_id = tx_resp.json()["items"][0]["transaction_id"]
    rec = client.post(f"/api/v1/transactions/{tx_id}/reconcile", headers=operator_headers)
    assert rec.status_code == 200
    excs = client.get(f"/api/v1/exceptions?transaction_id={tx_id}", headers=operator_headers)
    assert excs.status_code == 200
    return excs.json()["items"][0]


def test_at09_non_approver_blocked_and_at12_valid_approval_audited(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    op_headers = _login_headers(client, "operator@reconx-demo.com")
    app_headers = _login_headers(client, "approver@reconx-demo.com")
    aud_headers = _login_headers(client, "auditor@reconx-demo.com")

    case = _create_exception_for_scenario(client, op_headers, "AT-02")
    case_id = case["id"]

    # AT-09: Finance operator without approver role gets 403 and state stays OPEN
    denied = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=op_headers,
        json={"decision": "APPROVE", "rationale": "Trying to bypass role"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "APPROVAL_NOT_AUTHORIZED"
    unchanged = client.get(f"/api/v1/exceptions/{case_id}", headers=op_headers).json()
    assert unchanged["status"] == "OPEN"

    # Missing rationale is rejected
    no_rat = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=app_headers,
        json={"decision": "APPROVE", "rationale": "  ", "version": unchanged["version"]},
    )
    assert no_rat.status_code == 400
    assert no_rat.json()["error"]["code"] == "RATIONALE_REQUIRED"

    # Stale version returns 409 Conflict
    stale = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=app_headers,
        json={"decision": "APPROVE", "rationale": "Valid reason", "version": 999},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_CASE_VERSION"

    # AT-12: Approver approves with valid role, version, and rationale
    ok = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=app_headers,
        json={
            "decision": "APPROVE",
            "rationale": "Credit note received for 10 units; approved in workflow.",
            "version": unchanged["version"],
        },
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "APPROVED"

    # Illegal transition from terminal APPROVED state returns 409
    illegal = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=app_headers,
        json={"decision": "REJECT", "rationale": "Cannot change terminal state"},
    )
    assert illegal.status_code == 409
    assert illegal.json()["error"]["code"] == "ILLEGAL_STATE_TRANSITION"

    # Audit event recorded
    audit = client.get("/api/v1/audit?action=CASE_DECISION_APPROVE", headers=aud_headers)
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1


def test_maker_checker_approval_limit_and_notification_redaction(
    client: TestClient, test_db_session: Session
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    op_headers = _login_headers(client, "operator@reconx-demo.com")
    app_headers = _login_headers(client, "approver@reconx-demo.com")
    admin_headers = _login_headers(client, "admin@reconx-demo.com")

    case = _create_exception_for_scenario(client, op_headers, "AT-02")
    case_id = case["id"]

    # Assign case to approver -> triggers notification without leaking sensitive amounts/bank acct
    approver_user = (
        test_db_session.query(User).filter(User.email == "approver@reconx-demo.com").first()
    )
    assert approver_user is not None
    assign_resp = client.post(
        f"/api/v1/exceptions/{case_id}/assign",
        headers=op_headers,
        json={"owner_id": str(approver_user.id)},
    )
    assert assign_resp.status_code == 200

    notifs = client.get("/api/v1/notifications", headers=app_headers).json()
    assert len(notifs) >= 1
    assert "XXXX" not in notifs[0]["message"]
    assert "26432" not in notifs[0]["message"]

    # Maker-checker: HIGH severity case cannot be approved by its own owner
    mc_denied = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=app_headers,
        json={"decision": "APPROVE", "rationale": "Self approving"},
    )
    assert mc_denied.status_code == 403
    assert mc_denied.json()["error"]["code"] == "MAKER_CHECKER_VIOLATION"

    # Over-limit denial: lower approver limit below transaction amount and try admin vs approver
    client.put(
        "/api/v1/admin/config",
        headers=admin_headers,
        json={
            "config_json": {
                "approval_limits": {"approver": "100.00", "admin": "10000000.00"},
                "maker_checker_threshold": "100000.00",
            }
        },
    )
    # Reassign away from approver so limit check fires cleanly
    exc_row = test_db_session.get(ExceptionCase, __import__("uuid").UUID(case_id))
    assert exc_row is not None
    exc_row.owner_id = None
    test_db_session.commit()

    limit_denied = client.post(
        f"/api/v1/exceptions/{case_id}/decision",
        headers=app_headers,
        json={"decision": "APPROVE", "rationale": "Over my limit"},
    )
    assert limit_denied.status_code == 403
    assert limit_denied.json()["error"]["code"] == "APPROVAL_LIMIT_EXCEEDED"
