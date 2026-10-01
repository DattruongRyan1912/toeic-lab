"""Learner context for the AI mentor: everything that personalizes an answer, in a compact text block.

Built from the same services as the dashboard (no separate numbers), plus long-term memories.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from server.models import LearnerMemory
from server.services import coach, insights, planner, profile_service, skills
from server.utils import timeutil

MAX_MEMORIES = 25
STATUS_MARK = {"done": "✓", "skipped": "–", "pending": " "}


def memories(db: Session, user_id: int, limit: int = MAX_MEMORIES) -> list:
    return (
        db.query(LearnerMemory)
        .filter(LearnerMemory.user_id == user_id)
        .order_by(LearnerMemory.pinned.desc(), LearnerMemory.updated_at.desc(), LearnerMemory.id.desc())
        .limit(limit)
        .all()
    )


def build(db: Session, user_id: int, ai_online: bool = True) -> tuple:
    """(context text for the system prompt, dashboard dict)."""
    data = insights.build_dashboard(db, user_id)
    user = profile_service.get_user(db, user_id)
    profile = profile_service.serialize(user)
    report = skills.compute(db, user_id)
    prediction = skills.predict_score(report, user)
    retention = skills.srs_retention(db, user_id)

    exam = (
        f"Ngày thi {profile['exam_date'].strftime('%d/%m/%Y')} (còn {profile['days_to_exam']} ngày)"
        if profile["exam_date"] else "Chưa đặt ngày thi"
    )
    rca = ", ".join(f"{code} {count}" for code, count in data["rca_breakdown"].items() if count) or "chưa có"
    lines = [
        f"- Học viên: {data['display_name']}" + (f" ({data['headline']})" if data["headline"] else "")
        + f" | Mục tiêu {data['target_score']} ({data['target_cefr']}) | {exam}",
        f"- Lộ trình: tuần {data['current_week']}/{data['total_weeks']} (Phase {data['current_phase']}); học "
        f"{profile['daily_goal_minutes']} phút/ngày vào {planner.study_days_label(user.study_days)}; hôm nay đã học "
        f"{data['study_minutes_today']} phút; chuỗi {data['streak_days']} ngày",
        f"- Điểm dự đoán: {prediction['total']['expected']} (khoảng {prediction['total']['low']}-{prediction['total']['high']}; "
        f"L {prediction['listening']['expected']} [{prediction['listening']['basis']}], R {prediction['reading']['expected']} "
        f"[{prediction['reading']['basis']}]; độ tin cậy {round(prediction['confidence'] * 100)}%)",
    ]
    if profile["baseline_listening"] or profile["baseline_reading"]:
        lines.append(f"- Điểm đầu vào tự khai: L {profile['baseline_listening'] or '?'} / R {profile['baseline_reading'] or '?'}")
    weak = report.weakest_lessons(3)
    if weak:
        lines.append("- Chuyên đề yếu nhất: " + "; ".join(
            f"Bài {s.lesson_number:02d} {skills.percent(s.mastery)} ({s.attempts} câu, {s.open_errors} lỗi mở"
            + (f", xu hướng {round(s.trend * 100):+d}%" if s.trend is not None else "") + ")" for s in weak))
    strong = report.strongest_lessons(2)
    if strong:
        lines.append("- Chuyên đề vững: " + "; ".join(f"Bài {s.lesson_number:02d} {skills.percent(s.mastery)}" for s in strong))
    pace = [p for p in skills.pace_summary(report)]
    if pace:
        lines.append("- Tốc độ: " + "; ".join(
            f"{p['part']} {p['avg_seconds']}s/câu (mục tiêu {p['target_seconds']}s){' — chậm' if p['slow'] else ''}" for p in pace))
    lines.append(
        f"- SRS: {data['srs_due_count']} thẻ cần học hôm nay ({data['srs_review_due']} đến hạn + {data['srs_new_available']} mới, "
        f"{data['srs_new_cards_per_day']} thẻ mới/ngày); đã thuộc {data['srs_mastered_count']}/{data['total_flashcards']}"
        + (f"; tỉ lệ nhớ 30 ngày {round(retention['rate'] * 100)}%" if retention["rate"] is not None else "")
    )
    lines.append(f"- Sổ lỗi: {data['open_errors']} câu chưa nắm chắc, {data['error_reviews_due']} câu đến hạn ôn; RCA: {rca}")
    if data["learning_gaps"]:
        lines.append("- Lỗ hổng: " + "; ".join(
            f"{g['topic']} ({g['error_count']} lỗi" + (f" → Bài {g['lesson_number']:02d}" if g["lesson_number"] else "") + ")"
            for g in data["learning_gaps"][:3]))
    if data["today_tasks"]:
        lines.append("- Kế hoạch hôm nay: " + "; ".join(
            f"[{STATUS_MARK.get(t['status'], ' ')}] {t['title']}" + (f" ({t['estimated_minutes']}')" if t["estimated_minutes"] else "")
            for t in data["today_tasks"]))
    latest = data["latest_submission"]
    if latest is not None and latest.total_questions:
        lines.append(f"- Bài luyện gần nhất: {latest.part or latest.test_id} {latest.correct_count}/{latest.total_questions} "
                     f"({round((latest.correct_count or 0) / latest.total_questions * 100)}%)")
    tips = coach.top_lines(db, user_id, ai_online, limit=3, report=report)
    if tips:
        lines.append("- Gợi ý hệ thống: " + " | ".join(tips))
    lines.append(f"- Phong cách giải thích mong muốn: {profile_service.style_instruction(user)}")
    if profile["focus_parts"]:
        lines.append(f"- Part ưu tiên: {', '.join(profile['focus_parts'])}")
    if profile["learning_goal_note"]:
        lines.append(f"- Ghi chú mục tiêu: {profile['learning_goal_note']}")

    remembered = memories(db, user_id)
    if remembered:
        lines.append("ĐIỀU ĐÃ GHI NHỚ VỀ HỌC VIÊN (memory_id: nội dung):")
        lines.extend(f"- #{m.id} [{m.category}] {m.content}" for m in remembered)
    lines.append(f"- Hôm nay là {timeutil.local_today().strftime('%A %d/%m/%Y')} (giờ Việt Nam).")
    return "\n".join(lines), data
