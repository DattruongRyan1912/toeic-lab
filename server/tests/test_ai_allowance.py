"""AI allowance and usage accounting: quotas, exemptions for admins / granted accounts, key management."""
from datetime import timedelta

import httpx
import pytest

from server import config, models
from server.database import SessionLocal
from server.services import ai_agent_service, maintenance
from server.tests.conftest import make_user
from server.utils import timeutil

REPLY = {"candidates": [{"content": {"role": "model", "parts": [{"text": "Bản dịch"}]}}], "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 5, "totalTokenCount": 17}}


@pytest.fixture()
def gemini(monkeypatch):
    """Two configured Gemini keys answered by a mock; `seen` lists the keys used, `fail` the keys answering 429."""
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ["key-one", "key-two"])
    monkeypatch.setattr(config, "GEMINI_API_KEY", "key-one")
    monkeypatch.setattr(ai_agent_service, "_gemini_key_index", 0)
    state = {"seen": [], "fail": set()}

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers.get("x-goog-api-key")
        state["seen"].append(key)
        if key in state["fail"]:
            return httpx.Response(429, json={"error": {"code": 429}})
        return httpx.Response(200, json=REPLY)

    monkeypatch.setattr(ai_agent_service, "_http_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return state


def translate(client, headers=None):
    return client.post("/api/flashcards/translate-sentence", json={"sentence": "We leverage data."}, headers=headers or {})


def test_provider_calls_are_logged_with_tokens_and_key_alias(client, gemini):
    learner = make_user(client, "usage_learner")
    assert translate(client, learner["headers"]).json()["translation"] == "Bản dịch"
    with SessionLocal() as db:
        row = db.query(models.AIUsageLog).one()
    assert (row.user_id, row.endpoint, row.provider, row.key_alias, row.status) == (learner["id"], "translate", "gemini", "gemini-1", "ok")
    assert (row.prompt_tokens, row.completion_tokens, row.total_tokens) == (12, 5, 17) and row.latency_ms is not None


def test_default_plan_has_a_daily_quota(client, gemini, monkeypatch):
    monkeypatch.setattr(config, "AI_DAILY_QUOTA", 2)
    learner = make_user(client, "quota_learner")
    assert [translate(client, learner["headers"]).status_code for _ in range(3)] == [200, 200, 429]
    assert "hết 2 lượt AI" in translate(client, learner["headers"]).json()["detail"]
    quota = client.get("/api/ai/quota", headers=learner["headers"]).json()
    assert quota == {"plan": "default", "unlimited": False, "daily_quota": 2, "used_today": 2, "remaining": 0}

    timeutil.set_now(timeutil.utcnow() + timedelta(days=1))  # a new local day resets the count
    assert translate(client, learner["headers"]).status_code == 200


def test_failed_provider_calls_do_not_use_the_quota(client, gemini, monkeypatch):
    monkeypatch.setattr(config, "AI_DAILY_QUOTA", 1)
    gemini["fail"].update({"key-one", "key-two"})
    learner = make_user(client, "unlucky_learner")
    translate(client, learner["headers"])  # every key answers 429: nothing was delivered
    assert client.get("/api/ai/quota", headers=learner["headers"]).json()["used_today"] == 0


def test_admins_and_granted_accounts_skip_the_limits(client, gemini, monkeypatch, admin):
    monkeypatch.setattr(config, "AI_DAILY_QUOTA", 1)
    monkeypatch.setattr(config, "RATE_LIMIT_AI", "1/600")
    assert [translate(client, admin["headers"]).status_code for _ in range(3)] == [200, 200, 200]
    assert client.get("/api/ai/quota", headers=admin["headers"]).json()["plan"] == "admin"

    unlimited = make_user(client, "power_learner")
    custom = make_user(client, "custom_learner")
    assert client.patch(f"/api/admin/users/{unlimited['id']}", json={"ai_unlimited": True}, headers=admin["headers"]).json()["ai_plan"] == "unlimited"
    granted = client.patch(f"/api/admin/users/{custom['id']}", json={"ai_daily_quota": 3}, headers=admin["headers"]).json()
    assert (granted["ai_plan"], granted["ai_daily_quota"]) == ("custom", 3)

    assert [translate(client, unlimited["headers"]).status_code for _ in range(3)] == [200, 200, 200]
    # A custom quota replaces the default one and is not cut short by the burst limit.
    assert [translate(client, custom["headers"]).status_code for _ in range(4)] == [200, 200, 200, 429]

    reset = client.patch(f"/api/admin/users/{custom['id']}", json={"ai_daily_quota": None}, headers=admin["headers"]).json()
    assert (reset["ai_plan"], reset["ai_daily_quota"]) == ("default", 1)


def test_guests_have_a_small_daily_allowance(client, gemini, monkeypatch, production_mode):
    monkeypatch.setattr(config, "AI_GUEST_DAILY_QUOTA", 1)
    assert translate(client).status_code == 200
    blocked = translate(client)
    assert blocked.status_code == 429 and "Đăng nhập" in blocked.json()["detail"]


def test_rate_limited_key_rests_and_admin_can_switch_keys_off(client, gemini, admin):
    gemini["fail"].add("key-one")
    learner = make_user(client, "keys_learner")
    translate(client, learner["headers"])
    assert gemini["seen"] == ["key-one", "key-two"]  # 429 on key one, answered by key two
    gemini["seen"].clear()
    translate(client, learner["headers"])
    assert gemini["seen"][0] == "key-two"  # the rate-limited key rests instead of being tried first again

    off = client.patch("/api/admin/ai/keys/gemini-2", json={"disabled": True, "note": "hết hạn mức tháng"}, headers=admin["headers"])
    assert off.status_code == 200
    key = next(k for k in off.json()["keys"] if k["alias"] == "gemini-2")
    assert key["disabled"] and key["note"] == "hết hạn mức tháng" and key["ok_24h"] == 2
    gemini["seen"].clear()
    translate(client, learner["headers"])
    assert set(gemini["seen"]) == {"key-one"}
    assert client.patch("/api/admin/ai/keys/gemini-9", json={"disabled": True}, headers=admin["headers"]).status_code == 404


def test_admin_overview_reports_usage(client, gemini, admin):
    learner = make_user(client, "overview_learner")
    translate(client, learner["headers"])
    assert client.get("/api/admin/ai", headers=learner["headers"]).status_code == 403
    overview = client.get("/api/admin/ai", headers=admin["headers"]).json()
    assert overview["today"]["requests"] == 1 and overview["today"]["tokens"] == 17
    assert overview["top_users"][0]["username"] == "overview_learner"
    assert overview["by_endpoint"] == [{"endpoint": "translate", "requests": 1}]
    assert [k["alias"] for k in overview["keys"]] == ["gemini-1", "gemini-2"]
    assert overview["limits"]["daily_quota"] == config.AI_DAILY_QUOTA and overview["provider"]["provider"] == "gemini"
    rows = client.get("/api/admin/users", headers=admin["headers"]).json()["items"]
    assert next(r for r in rows if r["username"] == "overview_learner")["ai_requests_today"] == 1


def test_old_usage_logs_are_purged(client, gemini, db, monkeypatch):
    translate(client)
    timeutil.set_now(timeutil.utcnow() + timedelta(days=config.AI_USAGE_RETENTION_DAYS + 1))
    assert maintenance.run(db)["old_ai_usage_logs"] == 1
