from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_token, hash_password
from app.models.auth import Organization, Role, User


def _login(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "X-Correlation-ID" in resp.headers


def test_login_success_refresh_logout_and_me(client: TestClient) -> None:
    settings = get_settings()
    tokens = _login(client, "operator@reconx-demo.com", settings.seed_default_password)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert "finance_operator" in me.json()["roles"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    # Reusing old refresh token must fail
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "REFRESH_TOKEN_REVOKED"

    # Logout revokes new refresh token
    out = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert out.status_code == 200


def test_invalid_login_and_expired_token(client: TestClient, test_db_session: Session) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@reconx-demo.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    user = test_db_session.query(User).filter(User.email == "operator@reconx-demo.com").first()
    assert user is not None
    expired_token, _, _ = create_token(
        subject=str(user.id),
        organization_id=str(user.organization_id),
        roles=["finance_operator"],
        token_type="access",
        expires_delta=timedelta(seconds=-5),
    )
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_rbac_missing_permission_returns_403(client: TestClient) -> None:
    settings = get_settings()
    tokens = _login(client, "operator@reconx-demo.com", settings.seed_default_password)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Finance operator cannot access admin user creation or audit logs
    resp = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "new@reconx-demo.com",
            "full_name": "New User",
            "password": "StrongPassword#1",
            "roles": ["auditor"],
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    audit_resp = client.get("/api/v1/audit", headers=headers)
    assert audit_resp.status_code == 403


def test_cross_organization_isolation(client: TestClient, test_db_session: Session) -> None:
    settings = get_settings()
    other_org = Organization(
        name="Other Corp", base_currency="USD", timezone="UTC", settings_json={}
    )
    test_db_session.add(other_org)
    test_db_session.flush()

    admin_role = test_db_session.query(Role).filter(Role.name == "admin").first()
    assert admin_role is not None
    other_admin = User(
        organization_id=other_org.id,
        email="other-admin@other-demo.com",
        full_name="Other Admin",
        password_hash=hash_password("OtherAdmin#2026!"),
        status="ACTIVE",
        roles=[admin_role],
    )
    test_db_session.add(other_admin)
    test_db_session.commit()

    # Org 1 admin tries to update Org 2 user's roles -> 404 (not found in Org 1)
    org1_tokens = _login(client, "admin@reconx-demo.com", settings.seed_default_password)
    resp = client.patch(
        f"/api/v1/admin/users/{other_admin.id}/roles",
        headers={"Authorization": f"Bearer {org1_tokens['access_token']}"},
        json={"roles": ["auditor"]},
    )
    assert resp.status_code == 404

    # Org 1 admin lists users -> never sees other_admin
    users_resp = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {org1_tokens['access_token']}"},
    )
    assert users_resp.status_code == 200
    emails = [u["email"] for u in users_resp.json()["items"]]
    assert "other-admin@other-demo.com" not in emails


def test_login_rate_limiting(client: TestClient) -> None:
    settings = get_settings()
    for _ in range(settings.login_rate_limit_max_attempts):
        client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@reconx-demo.com", "password": "bad"},
        )
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@reconx-demo.com", "password": "bad"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "LOGIN_RATE_LIMITED"
