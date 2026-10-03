"""Tests for Authentic Topic Drill Bank isolation and ingestion."""

from server.data.authentic_drills import ALL_AUTHENTIC_DRILLS
from server.models import MockTest, TestQuestion
from scripts.ingest_authentic_drills import ingest_authentic_drills


def test_authentic_drill_data_integrity():
    """Verify all 12 drill packs have 15 authentic questions with 3D explanations."""
    assert len(ALL_AUTHENTIC_DRILLS) == 12

    total_questions = 0
    for test_id, name, lesson_no, questions in ALL_AUTHENTIC_DRILLS:
        assert test_id == f"DRILL_LESSON_{lesson_no:02d}"
        assert len(questions) == 15
        total_questions += len(questions)

        for q in questions:
            assert q["test_id"] == test_id
            assert q["lesson_number"] == lesson_no
            assert q["part"] == "Part 5"
            assert q["correct_choice"] in {"A", "B", "C", "D"}
            assert len(q["choice_a"]) > 0
            assert len(q["choice_b"]) > 0
            assert len(q["choice_c"]) > 0
            assert len(q["choice_d"]) > 0
            assert len(q["sentence"]) > 10
            assert "_______" in q["sentence"]
            assert len(q["explanation"]) > 20
            assert q["distractor_analysis"].startswith("[Bẫy")
            assert "=" in q["paraphrase_pair"]
            assert q["source"] == "Hackers TOEIC & ETS Grammar Drills"

    assert total_questions == 180


def test_drill_ingestion_and_api_isolation(db, client):
    """Verify drill ingestion into DB, API separation in /api/tests, and drill endpoint."""
    # Run ingestion into test DB
    stats = ingest_authentic_drills(db)
    assert stats["drills_added"] == 12
    assert stats["questions_added"] == 180

    # Ensure MockTest records have category='drill'
    drill_tests = db.query(MockTest).filter_by(category="drill").all()
    assert len(drill_tests) == 12

    # Verify GET /api/tests does NOT include any DRILL_% tests
    res = client.get("/api/tests")
    assert res.status_code == 200
    test_ids = [t["test_id"] for t in res.json()]
    for tid in test_ids:
        assert not tid.startswith("DRILL_"), f"Test {tid} should not appear in mock tests list"

    # Add KnowledgeLesson for lesson 5 so endpoint can verify it
    from server.models import KnowledgeLesson
    db.add(KnowledgeLesson(
        lesson_number=5,
        title="Bài 05: Hòa Hợp Chủ Ngữ - Vị Ngữ",
        subtitle="Subject-Verb Agreement",
        syntax_formula="S + V",
        summary="Quy tắc hòa hợp chủ vị",
        content_html="<p>Nội dung bài 05</p>",
    ))
    db.commit()

    # Verify GET /api/knowledge/lessons/5/drill returns 15 authentic drill questions
    drill_res = client.get("/api/knowledge/lessons/5/drill")
    assert drill_res.status_code == 200
    drill_questions = drill_res.json()
    assert len(drill_questions) == 15
    for q in drill_questions:
        assert q["test_id"] == "DRILL_LESSON_05"
        assert q["lesson_number"] == 5
