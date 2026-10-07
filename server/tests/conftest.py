"""Test harness: temporary SQLite DB, no .env, no API keys, no network."""
import os
import sys
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="toeic-tests-"))
os.environ["TOEIC_SKIP_DOTENV"] = "1"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test.db'}"
os.environ["CORS_ORIGINS"] = "http://localhost:3005"
os.environ["AI_PROVIDER"] = "auto"
os.environ["SECRET_KEY"] = "test-only-secret"
os.environ["SRS_NEW_CARDS_PER_DAY"] = "3"
for _key in ("GEMINI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    os.environ[_key] = ""

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from server import models  # noqa: E402
from server.database import Base, SessionLocal, engine, init_db  # noqa: E402
from server.main import app  # noqa: E402
from server.utils import rate_limit, timeutil  # noqa: E402
from server.utils.timeutil import utcnow  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    init_db()
    rate_limit.reset()
    yield
    timeutil.set_now(None)  # tests that time-travel must not leak a frozen clock


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


QUESTIONS = [
    # question_no, part, correct, distractor tag
    (101, "Part 5", "B", "[Bẫy Từ Loại] A là tính từ, C là danh từ."),
    (108, "Part 5", "D", "[Bẫy Vị Trí Trạng Từ] B là tính từ."),
    (111, "Part 5", "A", "[Bẫy Liên Từ vs Giới Từ] Because of + N."),
    (14, "Part 2", "C", "[Bẫy Similar Sound] A nghe giống câu hỏi."),
]


@pytest.fixture()
def seeded(db):
    """Minimal but complete dataset: user, roadmap, lessons, flashcards + SRS, one test."""
    user = db.get(models.User, 1)  # the app lifespan may already have created the default learner
    if user is None:
        db.add(models.User(id=1, username="learner", target_score=800, daily_goal_minutes=60))
    roadmap = models.Roadmap(user_id=1, title="Lộ trình 24 tuần", total_weeks=24, current_week=1)
    db.add(roadmap)
    db.flush()
    db.add_all(
        [
            models.SprintTask(roadmap_id=roadmap.id, phase=1, week_number=1, category="Syntax", title="Bài 01: Word forms", is_completed=True, completed_at=utcnow()),
            models.SprintTask(roadmap_id=roadmap.id, phase=1, week_number=2, category="Syntax", title="Bài 02 (Liên từ vs Giới từ)"),
            models.SprintTask(roadmap_id=roadmap.id, phase=2, week_number=9, category="Listening", title="Shadowing Part 3"),
        ]
    )
    for number, title in ((1, "Bài 01: Vị Trí 4 Loại Từ"), (2, "Bài 02: Liên Từ vs Giới Từ")):
        db.add(models.KnowledgeLesson(lesson_number=number, title=title, subtitle="sub", syntax_formula="S + V", summary="tóm tắt", content_html="<p>x</p>", content_md="## Nội dung"))
    now = utcnow()
    for index, word in enumerate(("postpone", "comply", "eligible", "reimburse", "allocate"), start=1):
        card = models.Flashcard(id=index, category="General Business", word=word, meaning=f"nghĩa {word}", example_sentence=f"We {word}.")
        db.add(card)
        db.flush()
        db.add(models.UserCardSRS(user_id=1, card_id=card.id, state="new", next_review_at=now))
    db.add(models.MockTest(test_id="ETS2024_01", name="ETS 2024 Test 01", year=2024, publisher="ETS", total_questions=200))
    db.flush()
    for number, part, correct, tag in QUESTIONS:
        db.add(
            models.TestQuestion(
                test_id="ETS2024_01", part=part, question_no=number, sentence=f"Question {number} ___.",
                choice_a="a", choice_b="b", choice_c="c", choice_d=None if part == "Part 2" else "d",
                correct_choice=correct, explanation=f"Giải thích {number}", distractor_analysis=tag,
                paraphrase_pair=f"pair {number}",
            )
        )
    db.add(models.ParaphrasePair(word_in_text="postpone", word_in_answer="delay", meaning="hoãn"))
    db.commit()
    return {q.question_no: q.id for q in db.query(models.TestQuestion).all()}


def make_user(client, username: str, role: str = "learner") -> dict:
    """Register a real account (optionally promoted) and return its Authorization header + id."""
    res = client.post("/api/auth/register", json={"username": username, "email": f"{username}@toeiclab.dev", "password": "Password123!"})
    assert res.status_code == 201, res.text
    client.cookies.clear()  # register sets an auth cookie; tests pass the header explicitly instead
    user_id = res.json()["user"]["id"]
    if role != "learner":
        with SessionLocal() as session:
            session.get(models.User, user_id).role = role
            session.commit()
    return {"id": user_id, "headers": {"Authorization": f"Bearer {res.json()['access_token']}"}}


@pytest.fixture()
def admin(client):
    return make_user(client, "site_admin", role="admin")
