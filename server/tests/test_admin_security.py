"""Admin console API and the security hardening around authentication."""
import pytest

from server import config
from server.database import SessionLocal
from server.models import User
from server.tests.conftest import make_user


@pytest.fixture()
def production_mode(monkeypatch):
    """Requests behave as in production: no test-only user_id fallbacks."""
    monkeypatch.delenv("TOEIC_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("TESTING", raising=False)


def test_admin_routes_require_admin_role(client, admin):
    learner = make_user(client, "plain_learner")
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/admin/users", headers=learner["headers"]).status_code == 403
    assert client.get("/api/admin/users", headers=admin["headers"]).status_code == 200


def test_admin_lists_filters_and_inspects_users(client, admin):
    learner = make_user(client, "alice_learner")
    res = client.get("/api/admin/users", headers=admin["headers"])
    body = res.json()
    usernames = {row["username"] for row in body["items"]}
    assert {"site_admin", "alice_learner"} <= usernames
    assert body["summary"]["admins"] == 1 and body["summary"]["total_users"] >= 2

    only_alice = client.get("/api/admin/users", params={"q": "ALICE"}, headers=admin["headers"]).json()
    assert [row["username"] for row in only_alice["items"]] == ["alice_learner"]
    admins = client.get("/api/admin/users", params={"role": "admin"}, headers=admin["headers"]).json()
    assert [row["username"] for row in admins["items"]] == ["site_admin"]

    detail = client.get(f"/api/admin/users/{learner['id']}", headers=admin["headers"]).json()
    assert detail["username"] == "alice_learner" and detail["has_password"] is True
    assert detail["submissions"] == 0 and detail["recent_submissions"] == []
    assert client.get("/api/admin/users/99999", headers=admin["headers"]).status_code == 404


def test_locking_a_user_revokes_access_and_login(client, admin):
    learner = make_user(client, "bob_learner")
    locked = client.patch(f"/api/admin/users/{learner['id']}", json={"is_active": False}, headers=admin["headers"])
    assert locked.status_code == 200 and locked.json()["is_active"] is False

    assert client.get("/api/auth/me", headers=learner["headers"]).status_code == 403
    assert client.get("/api/dashboard/stats", headers=learner["headers"]).status_code == 403
    login = client.post("/api/auth/login", json={"username_or_email": "bob_learner", "password": "Password123!"})
    assert login.status_code == 403

    client.patch(f"/api/admin/users/{learner['id']}", json={"is_active": True}, headers=admin["headers"])
    assert client.get("/api/auth/me", headers=learner["headers"]).status_code == 200


def test_role_changes_and_self_protection(client, admin):
    learner = make_user(client, "carol_learner")
    promoted = client.patch(f"/api/admin/users/{learner['id']}", json={"role": "admin"}, headers=admin["headers"])
    assert promoted.json()["role"] == "admin"
    assert client.get("/api/admin/users", headers=learner["headers"]).status_code == 200

    assert client.patch(f"/api/admin/users/{admin['id']}", json={"role": "learner"}, headers=admin["headers"]).status_code == 400
    assert client.patch(f"/api/admin/users/{admin['id']}", json={"is_active": False}, headers=admin["headers"]).status_code == 400
    assert client.patch(f"/api/admin/users/{learner['id']}", json={"role": "owner"}, headers=admin["headers"]).status_code == 422


def test_user_id_query_cannot_read_other_learners_in_production(client, production_mode):
    victim = make_user(client, "victim_learner")
    with SessionLocal() as db:
        db.get(User, victim["id"]).target_score = 955
        db.commit()
    # Without a token the guest learner is served, never the requested account.
    stats = client.get("/api/dashboard/stats", params={"user_id": victim["id"]}).json()
    assert stats["target_score"] != 955
    assert client.get("/api/error-logs", params={"user_id": victim["id"]}).status_code == 401


def test_password_less_account_cannot_be_claimed(client):
    with SessionLocal() as db:
        if db.get(User, config.DEFAULT_USER_ID) is None:
            db.add(User(id=config.DEFAULT_USER_ID, username="learner"))
        db.get(User, config.DEFAULT_USER_ID).hashed_password = None
        db.commit()
    res = client.post("/api/auth/login", json={"username_or_email": "learner", "password": "anything"})
    assert res.status_code == 400
    with SessionLocal() as db:
        assert db.get(User, config.DEFAULT_USER_ID).hashed_password is None


def test_forged_token_is_rejected(client):
    make_user(client, "real_user")
    forged = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl"
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_login_and_register_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_LOGIN", "3/900")
    monkeypatch.setattr(config, "RATE_LIMIT_REGISTER", "2/3600")
    bad = {"username_or_email": "nobody", "password": "wrong"}
    assert [client.post("/api/auth/login", json=bad).status_code for _ in range(4)] == [400, 400, 400, 429]
    # The limit is per identifier: another account is unaffected.
    assert client.post("/api/auth/login", json={**bad, "username_or_email": "someone"}).status_code == 400

    codes = [
        client.post("/api/auth/register", json={"username": f"spam{i}", "email": f"spam{i}@x.dev", "password": "Password123!"}).status_code
        for i in range(3)
    ]
    assert codes == [201, 201, 429]


def test_ai_endpoints_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_AI", "2/600")
    payload = {"sentence": "We leverage data."}
    codes = [client.post("/api/flashcards/translate-sentence", json=payload).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
