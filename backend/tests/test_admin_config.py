from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_admin_create_user_and_multi_role_support(client: TestClient) -> None:
    settings = get_settings()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@reconx-demo.com", "password": settings.seed_default_password},
    )
    assert login_resp.status_code == 200
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    create_resp = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "multi@reconx-demo.com",
            "full_name": "Multi Role User",
            "password": "MultiRole#2026!",
            "roles": ["finance_operator", "approver"],
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert sorted(created["roles"]) == ["approver", "finance_operator"]

    # New multi-role user can log in and holds permissions from both roles
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "multi@reconx-demo.com", "password": "MultiRole#2026!"},
    )
    assert new_login.status_code == 200
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
    )
    assert me.status_code == 200
    perms = set(me.json()["permissions"])
    assert "reconciliation:run" in perms
    assert "approvals:decide" in perms


def test_config_versioning_and_auditing(client: TestClient) -> None:
    settings = get_settings()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@reconx-demo.com", "password": settings.seed_default_password},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    get_v1 = client.get("/api/v1/admin/config", headers=headers)
    assert get_v1.status_code == 200
    assert get_v1.json()["version"] == 1

    put_v2 = client.put(
        "/api/v1/admin/config",
        headers=headers,
        json={"config_json": {"currency": "USD", "confidence_threshold": "0.85"}},
    )
    assert put_v2.status_code == 200
    assert put_v2.json()["version"] == 2
    assert put_v2.json()["is_active"] is True
