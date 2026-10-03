"""Unit and integration tests for authentication and multi-user data isolation."""
import pytest
from server.database import SessionLocal
from server.models import ErrorLog, Roadmap, User, UserCardSRS, UserTestSubmission


def test_register_provisions_isolated_workspace(client):
    db_init = SessionLocal()
    try:
        from server.models import Flashcard
        db_init.add(Flashcard(word="contract", word_type="noun", meaning="hợp đồng", example_sentence="sign a contract", category="Business"))
        db_init.commit()
    finally:
        db_init.close()

    res = client.post(
        "/api/auth/register",
        json={
            "username": "ryan_toeic",
            "email": "ryan@toeiclab.dev",
            "password": "Password123!",
            "display_name": "Ryan Truong",
            "target_score": 850,
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert "access_token" in data
    user_id = data["user"]["id"]
    assert data["user"]["username"] == "ryan_toeic"
    assert data["user"]["target_score"] == 850
    assert data["user"]["target_cefr"] is not None

    # Verify database was provisioned for this user
    db = SessionLocal()
    try:
        roadmap = db.query(Roadmap).filter_by(user_id=user_id).first()
        assert roadmap is not None
        assert "850+" in roadmap.title
        srs_count = db.query(UserCardSRS).filter_by(user_id=user_id).count()
        assert srs_count > 0
    finally:
        db.close()


def test_register_duplicate_prevention(client):
    payload = {
        "username": "duplicate_user",
        "email": "duplicate@toeiclab.dev",
        "password": "Password123!",
    }
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    # Same username, different email
    dup_name = client.post(
        "/api/auth/register",
        json={**payload, "email": "other@toeiclab.dev"},
    )
    assert dup_name.status_code == 400
    assert "Tên đăng nhập đã tồn tại" in dup_name.text

    # Different username, same email
    dup_email = client.post(
        "/api/auth/register",
        json={**payload, "username": "different_name"},
    )
    assert dup_email.status_code == 400
    assert "Email này đã được đăng ký" in dup_email.text


def test_login_and_auth_headers(client):
    # 1. /api/auth/me without token on fresh client -> 401
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    reg = client.post(
        "/api/auth/register",
        json={
            "username": "auth_tester",
            "email": "auth_tester@toeiclab.dev",
            "password": "MyStrongPassword123",
            "display_name": "Auth Tester",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    # Wrong password
    bad_login = client.post(
        "/api/auth/login",
        json={"username_or_email": "auth_tester", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 400

    # Correct password via username
    ok_user = client.post(
        "/api/auth/login",
        json={"username_or_email": "auth_tester", "password": "MyStrongPassword123"},
    )
    assert ok_user.status_code == 200
    assert ok_user.json()["access_token"] is not None

    # Correct password via email
    ok_email = client.post(
        "/api/auth/login",
        json={"username_or_email": "auth_tester@toeiclab.dev", "password": "MyStrongPassword123"},
    )
    assert ok_email.status_code == 200

    # /api/auth/me with Bearer token -> 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "auth_tester"


def test_multi_user_data_isolation(client):
    # 1. Create User A and User B
    res_a = client.post(
        "/api/auth/register",
        json={"username": "user_a", "email": "a@toeiclab.dev", "password": "passwordA123", "target_score": 800},
    )
    token_a = res_a.json()["access_token"]
    id_a = res_a.json()["user"]["id"]

    res_b = client.post(
        "/api/auth/register",
        json={"username": "user_b", "email": "b@toeiclab.dev", "password": "passwordB123", "target_score": 900},
    )
    token_b = res_b.json()["access_token"]
    id_b = res_b.json()["user"]["id"]

    assert id_a != id_b

    # 2. User A creates an error log
    create_err = client.post(
        "/api/error-logs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "test_id": "ETS2024_01",
            "part": "Part 5",
            "question_no": 105,
            "error_type": "GRAMMAR",
            "user_choice": "A",
            "correct_choice": "C",
            "root_cause": "Nhầm lẫn giữa tính từ và danh từ.",
            "key_rule_or_paraphrase": "Sau mạo từ là danh từ",
        },
    )
    assert create_err.status_code == 201

    # 3. User A queries error logs -> sees 1 error
    logs_a = client.get("/api/error-logs", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert len(logs_a) == 1

    # 4. User B queries error logs -> sees 0 errors! Complete isolation!
    logs_b = client.get("/api/error-logs", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert len(logs_b) == 0

    # 5. User A dashboard reflects User A target 800, User B reflects 900
    dash_a = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_a}"}).json()
    dash_b = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert dash_a["target_score"] == 800
    assert dash_b["target_score"] == 900
