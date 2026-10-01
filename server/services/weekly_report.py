"""Weekly progress report: what changed over the last 7 days and what to focus on next.

Shown on Analytics, read by the AI mentor (tool `get_weekly_report`) and sent by the Telegram reminder.
Mastery deltas compare two skill snapshots (`skills.compute(now=...)`), so they reflect real attempts only.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from server.models import ErrorLog, QuestionAttempt, SRSReviewLog, StudySession
from server.services import activity, error_log_service, insights, planner, skills
from server.utils import timeutil

CHANGE_THRESHOLD = 0.03  # mastery moves smaller than 3 points are noise
KIND_LABELS = {
    "srs": "Từ vựng SRS", "practice": "Luyện đề", "review": "Ôn câu sai", "lesson": "Đọc bài", "mentor": "AI Mentor",
    "listening": "Listening", "reading": "Reading", "other": "Khác",
}


def _pct(value: Optional[float]) -> Optional[int]:
    return None if value is None else round(value * 100)


def _accuracy(rows: list) -> Optional[float]:
    return round(sum(1 for r in rows if r.is_correct) / len(rows), 3) if rows else None


def build(db: Session, user_id: int, end: Optional[date] = None) -> dict:
    user = insights.get_or_create_user(db, user_id)
    settings = planner.learner_settings(user)
    end = end or timeutil.local_today()  # inclusive
    start = end - timedelta(days=6)
    start_utc = timeutil.local_day_start_utc(start)
    end_utc = min(timeutil.local_day_start_utc(end + timedelta(days=1)), timeutil.utcnow())
    prev_start_utc = timeutil.local_day_start_utc(start - timedelta(days=7))

    # --- study time
    by_kind: Counter = Counter()
    by_day: Counter = Counter()
    for session in activity.sessions_between(db, user_id, start, end + timedelta(days=1)):
        by_kind[session.kind] += session.duration_seconds or 0
        by_day[timeutil.local_date_of(session.started_at)] += session.duration_seconds or 0
    today = timeutil.local_today()
    # the day in progress is not judged yet: its minutes count, its goal and pending tasks do not
    planned_days = sum(
        1 for i in range(7)
        if (start + timedelta(days=i)).weekday() in settings.study_days and start + timedelta(days=i) < today
    )
    minutes = round(sum(by_kind.values()) / 60)
    goal = settings.daily_minutes * planned_days

    # --- practice (this week vs the week before)
    def attempts(since, until):
        return (
            db.query(QuestionAttempt)
            .filter(QuestionAttempt.user_id == user_id, QuestionAttempt.created_at >= since, QuestionAttempt.created_at < until)
            .all()
        )

    week_rows, prev_rows = attempts(start_utc, end_utc), attempts(prev_start_utc, start_utc)
    times = [r.time_ms for r in week_rows if r.time_ms]
    accuracy, prev_accuracy = _accuracy(week_rows), _accuracy(prev_rows)

    # --- mastery snapshots
    before = skills.compute(db, user_id, now=start_utc)
    after = skills.compute(db, user_id, now=end_utc)
    changes = []
    for number, stat in after.lessons.items():
        old = before.lessons[number]
        if stat.attempts == old.attempts:
            continue  # not practised this week
        changes.append({
            "lesson_number": number, "title": stat.label, "attempts": stat.attempts - old.attempts,
            "mastery_before": round(old.mastery, 3), "mastery_after": round(stat.mastery, 3),
            "delta": round(stat.mastery - old.mastery, 3), "first_time": old.attempts == 0,
        })
    changes.sort(key=lambda c: c["delta"], reverse=True)
    pred_before, pred_after = skills.predict_score(before, user), skills.predict_score(after, user)

    # --- mistakes
    errors_new = db.query(ErrorLog).filter(
        ErrorLog.user_id == user_id, ErrorLog.created_at >= start_utc, ErrorLog.created_at < end_utc
    ).count()
    errors_mastered = db.query(ErrorLog).filter(
        ErrorLog.user_id == user_id, ErrorLog.status == "mastered",
        ErrorLog.last_reviewed_at >= start_utc, ErrorLog.last_reviewed_at < end_utc,
    ).count()
    errors_open = db.query(ErrorLog).filter(ErrorLog.user_id == user_id, error_log_service.open_filter()).count()
    reviews_next_week = sum(planner.error_reviews_by_day(db, user_id, end + timedelta(days=1), 7).values())

    # --- vocabulary
    ratings = db.query(SRSReviewLog.rating, SRSReviewLog.prev_state).filter(
        SRSReviewLog.user_id == user_id, SRSReviewLog.reviewed_at >= start_utc, SRSReviewLog.reviewed_at < end_utc
    ).all()
    old_cards = [rating for rating, prev in ratings if prev != "new"]

    # --- plan
    items = [
        i for i in planner.list_items(db, user_id, start, end + timedelta(days=1))
        if i["status"] == "done" or (i["status"] == "pending" and i["date"] < today)
    ]
    done_items = sum(1 for i in items if i["status"] == "done")

    new_learner = not week_rows and not prev_rows and not db.query(StudySession.id).filter(
        StudySession.user_id == user_id, StudySession.started_at < end_utc
    ).first()

    report = {
        "start": start, "end": end, "new_learner": new_learner,
        "study": {
            "minutes": minutes, "goal_minutes": goal, "goal_rate": round(minutes / goal, 3) if goal else None,
            "active_days": sum(1 for seconds in by_day.values() if seconds >= 60), "planned_days": planned_days,
            "by_kind": {KIND_LABELS.get(k, k): round(v / 60) for k, v in by_kind.most_common() if v >= 30},
        },
        "practice": {
            "questions": len(week_rows), "correct": sum(1 for r in week_rows if r.is_correct),
            "accuracy": accuracy, "previous_accuracy": prev_accuracy,
            "accuracy_delta": round(accuracy - prev_accuracy, 3) if accuracy is not None and prev_accuracy is not None else None,
            "avg_seconds": round(sum(times) / len(times) / 1000, 1) if times else None,
        },
        "mastery_changes": changes,
        "prediction": {
            "total": pred_after["total"]["expected"], "previous_total": pred_before["total"]["expected"],
            "delta": pred_after["total"]["expected"] - pred_before["total"]["expected"],
            "confidence": pred_after["confidence"], "target": pred_after["target_score"],
        },
        "errors": {"new": errors_new, "mastered": errors_mastered, "open": errors_open, "reviews_next_week": reviews_next_week},
        "vocab": {
            "reviews": len(ratings), "new_cards": sum(1 for _, prev in ratings if prev == "new"),
            "retention": round(sum(1 for r in old_cards if r >= 2) / len(old_cards), 3) if old_cards else None,
        },
        "plan": {"items": len(items), "done": done_items, "completion": round(done_items / len(items), 3) if items else None},
        "next_focus": [
            {"lesson_number": f.lesson_number, "title": f.title, "reason": f.reason}
            for f in planner.focus_lessons(db, user_id, after, insights.get_roadmap(db, user_id))
        ],
        "days_to_exam": planner.days_to_exam(settings, end),
    }
    report["highlights"], report["recommendations"] = _narrative(report)
    return report


def _narrative(r: dict) -> tuple[list, list]:
    highlights, todo = [], []
    if r["new_learner"]:
        todo.append("Tuần đầu tiên: hoàn tất cá nhân hoá (2 phút) rồi làm 15 câu Luyện thông minh để hệ thống đo năng lực của bạn.")
        if r["next_focus"]:
            todo.append("Gợi ý bắt đầu: " + "; ".join(f["title"] for f in r["next_focus"][:2]) + ".")
        return highlights, todo
    study, practice, errors = r["study"], r["practice"], r["errors"]
    if study["goal_minutes"]:
        highlights.append(f"Học {study['minutes']}/{study['goal_minutes']} phút ({_pct(study['goal_rate'])}% mục tiêu), {study['active_days']}/{study['planned_days']} ngày học")
    if practice["questions"]:
        line = f"Làm {practice['questions']} câu, đúng {_pct(practice['accuracy'])}%"
        if practice["accuracy_delta"] is not None:
            line += f" ({'+' if practice['accuracy_delta'] >= 0 else ''}{_pct(practice['accuracy_delta'])} điểm so với tuần trước)"
        highlights.append(line)
    improved = [c for c in r["mastery_changes"] if c["delta"] >= CHANGE_THRESHOLD]
    declined = [c for c in r["mastery_changes"] if c["delta"] <= -CHANGE_THRESHOLD]
    if improved:
        highlights.append("Tiến bộ: " + ", ".join(f"Bài {c['lesson_number']:02d} +{_pct(c['delta'])}%" for c in improved[:3]))
    if declined:
        highlights.append("Đi xuống: " + ", ".join(f"Bài {c['lesson_number']:02d} {_pct(c['delta'])}%" for c in declined[:3]))
    if errors["mastered"]:
        highlights.append(f"Đã nắm chắc {errors['mastered']} câu sai")
    if r["prediction"]["delta"]:
        highlights.append(f"Điểm dự đoán {r['prediction']['previous_total']} → {r['prediction']['total']}")

    if study["goal_rate"] is not None and study["goal_rate"] < 0.5:
        todo.append("Tuần qua đạt dưới 50% thời gian mục tiêu — giữ một khung giờ cố định mỗi ngày, hoặc giảm phút/ngày cho vừa sức.")
    if not practice["questions"]:
        todo.append("Chưa làm câu nào trong tuần — làm 15 câu Luyện thông minh để hệ thống đo lại năng lực.")
    if errors["reviews_next_week"]:
        todo.append(f"Ôn {errors['reviews_next_week']} câu sai đến hạn trong 7 ngày tới (lịch 1 → 3 → 7 ngày).")
    for c in declined[:1]:
        todo.append(f"Ôn lại {c['title']} — mastery giảm {abs(_pct(c['delta']))}%.")
    if r["vocab"]["retention"] is not None and r["vocab"]["retention"] < 0.75 and r["vocab"]["reviews"] >= 20:
        todo.append(f"Tỉ lệ nhớ thẻ {_pct(r['vocab']['retention'])}% — giảm thẻ mới/ngày để nhớ chắc hơn.")
    if r["next_focus"]:
        todo.append("Trọng tâm tuần tới: " + "; ".join(f["title"] for f in r["next_focus"][:2]) + ".")
    return highlights, todo


def to_markdown(r: dict) -> str:
    lines = [f"📊 *Báo cáo tuần {r['start']:%d/%m} – {r['end']:%d/%m}*"]
    if r["days_to_exam"] is not None and r["days_to_exam"] >= 0:
        lines[0] += f" • còn {r['days_to_exam']} ngày thi"
    lines += [f"• {line}" for line in r["highlights"]] or ["• Chưa có hoạt động học trong tuần."]
    if r["recommendations"]:
        lines.append("\n*Tuần tới:*")
        lines += [f"→ {line}" for line in r["recommendations"]]
    return "\n".join(lines)
