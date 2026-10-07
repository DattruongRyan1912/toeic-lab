"""Contract between the API and apps/web/types/index.ts: every field the new pages read must be present.

The web app renders client-side, so a missing key would only show up as a blank widget in the browser;
this test catches such drift at the API level.
"""


def keys(obj: dict, *names: str, where: str = "") -> None:
    missing = [name for name in names if name not in obj]
    assert not missing, f"{where}: missing {missing}"


def test_payloads_match_frontend_types(client, seeded):
    # create some learner data: one wrong answer (error log + attempt), one audited tool action, one note
    submit = client.post("/api/practice/submit", json={
        "answers": [{"question_id": seeded[101], "choice": "A", "time_ms": 21000}], "mode": "study", "part": "Part 5", "time_spent_seconds": 25,
    })
    assert submit.status_code == 200, submit.text
    result = submit.json()
    keys(result, "mode", "reviews_advanced", "errors_mastered", "avg_time_seconds", "time_spent_seconds", "errors_logged", "unanswered",
         "accuracy", "correct_count", "total_questions", "part", "lesson_number", "learning_gaps", "scaled_reading", "results", where="submit")
    keys(result["results"][0], "question_id", "question_no", "test_id", "time_ms", "review_outcome", "user_choice", "correct_choice",
         "is_correct", "error_type", "trap_tag", "lesson_number", "part", where="submit.results")
    if result["learning_gaps"]:
        keys(result["learning_gaps"][0], "id", "topic", "error_count", "lesson_number", "lesson_title", where="learning_gaps")
    action = client.post("/api/ai/actions/execute", json={"tool": "remember_learner_fact", "args": {"content": "Thích ví dụ về deploy"}, "source": "user"})
    assert action.status_code == 200, action.text
    keys(action.json(), "tool", "status", "message", "writes", "action_id", "undoable", where="execute")
    assert client.post("/api/knowledge/lessons/1/notes", json={"content": "Trạng từ đứng trước động từ thường"}).status_code == 201

    week = client.get("/api/plan/week").json()
    keys(week, "start", "end", "generated_on", "settings", "focus", "days", "history", where="plan")
    keys(week["settings"], "daily_minutes", "planned_daily_minutes", "auto_adjust", "adjustments", "study_days", "new_cards_per_day",
         "exam_date", "days_to_exam", "focus_parts", where="plan.settings")
    keys(week["history"], "days", "planned_items", "done_items", "completion_rate", "studied_minutes", "goal_minutes", "behind", where="plan.history")
    keys(week["days"][0], "date", "weekday", "is_today", "is_study_day", "planned_minutes", "done_minutes", "studied_minutes", "items", where="plan.day")
    items = [item for day in week["days"] for item in day["items"]]
    assert items, "seeded learner should get a plan"
    keys(items[0], "id", "date", "kind", "tag", "title", "detail", "reason", "lesson_number", "part", "target_count", "progress",
         "estimated_minutes", "priority", "status", "auto", "source", "href", "ref", where="plan.item")
    assert all(item["href"].startswith("/") for item in items)
    if week["focus"]:
        keys(week["focus"][0], "lesson_number", "title", "mastery", "status", "attempts", "open_errors", "question_count", "reason", where="plan.focus")

    insights = client.get("/api/learner/insights").json()
    keys(insights, "lessons", "parts", "sections", "prediction", "pace", "srs_retention", "leech_cards", "study_minutes", "total_attempts", where="insights")
    keys(insights["lessons"][0], "key", "label", "kind", "lesson_number", "part", "attempts", "distinct_questions", "mastery", "confidence",
         "trend", "avg_time_seconds", "target_seconds", "open_errors", "question_count", "status", where="insights.skill")
    prediction = insights["prediction"]
    keys(prediction, "listening", "reading", "total", "confidence", "target_score", "target_gap", "coverage", "measured_parts",
         "unmeasurable_parts", where="prediction")
    keys(prediction["listening"], "expected", "low", "high", "basis", "confidence", where="prediction.listening")
    keys(prediction["total"], "expected", "low", "high", "cefr", where="prediction.total")
    keys(insights["srs_retention"], "reviews", "retained", "rate", where="srs_retention")
    keys(insights["study_minutes"][-1], "date", "minutes", "goal_minutes", "by_kind", where="study_minutes")
    assert insights["study_minutes"][-1]["minutes"] >= 0
    for row in insights["pace"]:
        keys(row, "part", "avg_seconds", "target_seconds", "slow", where="pace")

    for item in client.get("/api/learner/suggestions").json():
        keys(item, "id", "title", "detail", "priority", "kind", "cta", "tool", "args", "href", "prompt", where="suggestion")
    logs = client.get("/api/ai/actions?limit=5&v=1").json()  # the UI adds a cache-busting `v`
    keys(logs[0], "id", "tool", "source", "summary", "status", "undoable", "created_at", "undone_at", where="ai.actions")
    keys(client.get("/api/ai/tools").json()[0], "name", "description", "writes", "category", where="ai.tools")
    keys(client.get("/api/learner/memories").json()[0], "id", "category", "content", "source", "pinned", "created_at", "updated_at", where="memory")

    profile = client.get("/api/learner/profile").json()
    keys(profile, "exam_date", "days_to_exam", "baseline_listening", "baseline_reading", "study_days", "new_cards_per_day",
         "effective_new_cards_per_day", "explanation_style", "focus_parts", "learning_goal_note", "auto_adjust", "onboarded", where="profile")
    stats = client.get("/api/dashboard/stats").json()
    keys(stats, "onboarded", "exam_date", "days_to_exam", "error_reviews_due", "predicted_score", "study_minutes_today", where="dashboard")

    lesson = client.get("/api/knowledge/lessons/1").json()
    keys(lesson, "notes", "progress", "stats", where="lesson")
    keys(lesson["stats"], "mastery", "confidence", "attempts", "avg_time_seconds", "trend", where="lesson.stats")
    keys(lesson["notes"][0], "id", "lesson_number", "content", "source", "created_at", where="lesson.note")
    progress = client.post("/api/knowledge/lessons/1/progress", json={"event": "view"}).json()
    keys(progress, "lesson_number", "time_spent_seconds", "view_count", "completed_at", where="lesson.progress")

    error = client.get("/api/error-logs").json()[0]
    keys(error, "review_stage", "next_review_at", "question_id", "lesson_number", where="error_log")
    submission = client.get("/api/tests/submissions?limit=10").json()[0]
    keys(submission, "id", "submitted_at", "mode", "lesson_number", "part", "correct_count", "total_questions", "accuracy", "time_spent_seconds", where="submission")
    for path in ("/api/practice/smart?count=15", "/api/practice/review-queue?limit=30"):
        questions = client.get(path).json()
        if questions:
            keys(questions[0], "id", "test_id", "question_no", "part", "sentence", "choice_a", "correct_choice", "reason", where=path)
    for pair in client.get("/api/knowledge/paraphrases?limit=3").json():
        keys(pair, "id", "word_in_text", "word_in_answer", "meaning", "context_example", "part_target", where="paraphrase")


def test_weekly_report_matches_frontend_type(client, seeded):
    report = client.get("/api/learner/weekly-report").json()
    keys(report, "start", "end", "study", "practice", "mastery_changes", "prediction", "errors", "vocab", "plan", "next_focus",
         "days_to_exam", "highlights", "recommendations", "markdown", where="weekly")
    keys(report["study"], "minutes", "goal_minutes", "goal_rate", "active_days", "planned_days", "by_kind", where="weekly.study")
    keys(report["practice"], "questions", "correct", "accuracy", "previous_accuracy", "accuracy_delta", "avg_seconds", where="weekly.practice")
    keys(report["prediction"], "total", "previous_total", "delta", "confidence", "target", where="weekly.prediction")
    keys(report["errors"], "new", "mastered", "open", "reviews_next_week", where="weekly.errors")
    keys(report["vocab"], "reviews", "new_cards", "retention", where="weekly.vocab")
    keys(report["plan"], "items", "done", "completion", where="weekly.plan")
