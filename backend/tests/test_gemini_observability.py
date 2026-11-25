import json
from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.llm.adapter import GeminiLLMProvider, get_llm_provider
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_gemini_provider_selection_and_missing_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    get_settings.cache_clear()

    prov = get_llm_provider()
    assert isinstance(prov, GeminiLLMProvider)
    assert prov.model_name == "gemini-2.5-flash"

    out = prov.explain({"task": "summarize"})
    assert out is None
    assert prov.last_telemetry is not None
    assert prov.last_telemetry.configured_provider == "gemini"
    assert prov.last_telemetry.actual_provider == "mock"
    assert prov.last_telemetry.fallback_used is True
    assert prov.last_telemetry.error_category == "MISSING_API_KEY"

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()


def test_gemini_valid_response_and_error_categories(monkeypatch) -> None:
    prov = GeminiLLMProvider("secret-test-key", "gemini-2.5-flash", 5)

    # 1. Valid response
    ok_resp = MagicMock()
    ok_resp.raise_for_status.return_value = None
    ok_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({"summary": "Live summary"})}]}}]
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value.post.return_value = ok_resp
    monkeypatch.setattr(httpx, "Client", lambda timeout: mock_client)

    res = prov.explain({"task": "summarize"})
    assert res == {"summary": "Live summary"}
    assert prov.last_telemetry is not None
    assert prov.last_telemetry.success is True
    assert prov.last_telemetry.fallback_used is False
    assert prov.last_telemetry.actual_provider == "gemini"

    # 2. Invalid JSON response
    bad_json_resp = MagicMock()
    bad_json_resp.raise_for_status.return_value = None
    bad_json_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "not-valid-json"}]}}]
    }
    mock_client.__enter__.return_value.post.return_value = bad_json_resp
    assert prov.explain({"task": "summarize"}) is None
    assert prov.last_telemetry.error_category == "INVALID_RESPONSE"
    assert prov.last_telemetry.fallback_used is True

    # 3. Timeout
    mock_client.__enter__.return_value.post.side_effect = httpx.TimeoutException("timed out")
    assert prov.explain({"task": "summarize"}) is None
    assert prov.last_telemetry.error_category == "TIMEOUT"

    # 4. Auth error (401)
    req = httpx.Request("POST", "https://example.com")
    mock_client.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
        "401", request=req, response=httpx.Response(401, request=req)
    )
    assert prov.explain({"task": "summarize"}) is None
    assert prov.last_telemetry.error_category == "AUTH_ERROR"

    # 5. Rate limit (429)
    mock_client.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
        "429", request=req, response=httpx.Response(429, request=req)
    )
    assert prov.explain({"task": "summarize"}) is None
    assert prov.last_telemetry.error_category == "RATE_LIMITED"


def test_gemini_telemetry_attribution_and_key_secrecy(
    client: TestClient, test_db_session: Session, monkeypatch
) -> None:
    seed_synthetic_dataset(test_db_session, reset=True)
    op = _login_headers(client, "operator@reconx-demo.com")
    admin = _login_headers(client, "admin@reconx-demo.com")

    # Configure gemini with fake secret key and mock HTTP 200
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyFakeSecretDoNotExpose12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    get_settings.cache_clear()

    ok_resp = MagicMock()
    ok_resp.raise_for_status.return_value = None
    ok_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({"summary": "Gemini ok"})}]}}]
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value.post.return_value = ok_resp
    monkeypatch.setattr(httpx, "Client", lambda timeout: mock_client)

    # Admin-only test connection endpoint
    assert client.post("/api/v1/intelligence/gemini/test", headers=op).status_code == 403
    t_res = client.post("/api/v1/intelligence/gemini/test", headers=admin)
    assert t_res.status_code == 200
    tdata = t_res.json()
    assert tdata["connected"] is True
    assert tdata["model"] == "gemini-2.5-flash"
    assert "AIzaSyFakeSecretDoNotExpose12345" not in t_res.text

    # Run investigation on AT-02 -> attributed to gemini
    tx2 = client.get("/api/v1/transactions?scenario_label=AT-02", headers=op).json()["items"][0]
    client.post(f"/api/v1/transactions/{tx2['transaction_id']}/reconcile", headers=op)
    exc_id = client.get(
        f"/api/v1/exceptions?transaction_id={tx2['transaction_id']}", headers=op
    ).json()["items"][0]["id"]
    inv = client.post(f"/api/v1/exceptions/{exc_id}/investigations", headers=op)
    assert inv.status_code == 201
    idata = inv.json()
    assert idata["actual_provider"] == "gemini"
    assert idata["llm_succeeded"] is True
    assert idata["fallback_used"] is False

    # Harness telemetry reflects real calls & never exposes API key
    harness = client.get("/api/v1/intelligence/agent-harness", headers=op)
    assert harness.status_code == 200
    assert "AIzaSyFakeSecretDoNotExpose12345" not in harness.text
    gtel = harness.json()["gemini_telemetry"]
    assert gtel["invocation_count"] >= 2
    assert gtel["successful_calls"] >= 2
    assert gtel["token_usage_available"] is False

    # Now simulate Gemini failure -> fallback attributed to mock, NOT gemini
    mock_client.__enter__.return_value.post.side_effect = httpx.TimeoutException("timeout")
    inv2 = client.post(f"/api/v1/exceptions/{exc_id}/investigations", headers=op)
    assert inv2.status_code == 201
    i2 = inv2.json()
    assert i2["actual_provider"] == "mock"
    assert i2["llm_succeeded"] is False
    assert i2["fallback_used"] is True

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()
