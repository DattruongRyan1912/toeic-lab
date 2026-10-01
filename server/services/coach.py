"""Coach: proactive, data-driven suggestions with a one-click action.

Each suggestion explains the evidence and carries an action:
  * kind "tool"   -> POST /api/ai/actions/execute {tool, args} (audited + undoable)
  * kind "mentor" -> open the AI mentor with a prepared prompt (the model then uses tools)
  * kind "link"   -> navigate to the page where the learner does it
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from server.models import ErrorLog, Flashcard, StudyReminder
from server.services import activity, error_log_service, insights, planner, skills
from server.utils import timeutil


def _suggestion(sid: str, title: str, detail: str, priority: int, kind: str, cta: str, **action) -> dict:
    return {"id": sid, "title": title, "detail": detail, "priority": priority, "kind": kind, "cta": cta,
            "tool": action.get("tool"), "args": action.get("args") or {}, "href": action.get("href"), "prompt": action.get("prompt")}


def suggestions(db: Session, user_id: int, ai_online: bool = True, limit: int = 6, report=None) -> list:
    user = insights.get_or_create_user(db, user_id)
    report = report or skills.compute(db, user_id)
    settings = planner.learner_settings(user)
    today = timeutil.local_today()
    items: list = []

    if user.onboarded_at is None:
        items.append(_suggestion(
            "onboarding", "Thiết lập hồ sơ cá nhân hoá (2 phút)",
            "Cho biết ngày thi, điểm hiện tại và thời gian rảnh — lộ trình, kế hoạch hằng ngày và AI Mentor sẽ bám theo bạn.",
            100, "link", "Bắt đầu", href="/onboarding",
        ))
    elif user.exam_date is None:
        items.append(_suggestion(
            "exam_date", "Đặt ngày thi để lộ trình tự co giãn",
            "Có ngày thi, các mốc 24 tuần sẽ được nén/giãn cho vừa và kế hoạch tăng thi thử khi gần ngày thi.",
            70, "link", "Đặt ngày thi", href="/settings#personalization",
        ))

    due = error_log_service.due_reviews(db, user_id)
    if due:
        items.append(_suggestion(
            "error_reviews_due", f"Ôn {len(due)} câu sai đến hạn",
            "Làm đúng 3 lần cách nhau 1-3-7 ngày thì câu sai tự chuyển 'Đã nắm chắc' và lỗ hổng tự đóng.",
            90, "link", "Ôn ngay", href="/mock-tests?mode=review",
        ))

    week = planner.week_view(db, user_id, report=report)
    history = week["history"]
    if history["behind"]:
        items.append(_suggestion(
            "replan", "Bạn đang chậm kế hoạch — lập lại 7 ngày tới?",
            f"Tuần qua hoàn thành {history['done_items']}/{history['planned_items']} nhiệm vụ. Kế hoạch mới sẽ dồn trọng tâm vào việc quan trọng nhất.",
            80, "tool", "Lập lại kế hoạch", tool="replan_week", args={"reason": "behind_schedule"},
        ))

    retention = skills.srs_retention(db, user_id)
    per_day = settings.new_cards_per_day
    if retention["rate"] is not None and retention["reviews"] >= 20:
        if retention["rate"] < 0.75 and per_day > 5:
            new_value = max(5, per_day - 5)
            items.append(_suggestion(
                "srs_lower", f"Giảm thẻ mới còn {new_value}/ngày",
                f"Tỉ lệ nhớ 30 ngày chỉ {round(retention['rate'] * 100)}% ({retention['reviews']} lượt ôn) — học ít thẻ mới hơn để nhớ chắc hơn.",
                75, "tool", "Áp dụng", tool="update_learner_profile", args={"new_cards_per_day": new_value},
            ))
        elif retention["rate"] > 0.92 and retention["reviews"] >= 30 and per_day < 30:
            new_value = min(30, per_day + 5)
            items.append(_suggestion(
                "srs_raise", f"Tăng thẻ mới lên {new_value}/ngày",
                f"Tỉ lệ nhớ {round(retention['rate'] * 100)}% — bạn nhớ rất tốt, có thể tăng tốc nạp từ vựng.",
                50, "tool", "Áp dụng", tool="update_learner_profile", args={"new_cards_per_day": new_value},
            ))

    srs = insights.srs_counts(db, user_id)
    if srs["review_due"] > 60 and per_day > 0:
        items.append(_suggestion(
            "srs_backlog", "Tạm dừng thẻ mới để xử lý tồn đọng",
            f"Đang có {srs['review_due']} thẻ quá hạn. Dừng thẻ mới vài ngày giúp phiên ôn gọn và hiệu quả hơn.",
            72, "tool", "Tạm dừng thẻ mới", tool="update_learner_profile", args={"new_cards_per_day": 0},
        ))

    if ai_online:
        for stat in report.weakest_lessons(2, min_attempts=3):
            if stat.status == "weak" and stat.unseen_questions < 3:
                items.append(_suggestion(
                    f"ai_practice_{stat.lesson_number}", f"Tạo câu luyện mới cho {stat.label}",
                    f"Mastery {skills.percent(stat.mastery)} và chỉ còn {stat.unseen_questions} câu chưa làm — AI tạo 5 câu nhắm đúng bẫy bạn hay sai.",
                    65, "mentor", "Nhờ AI tạo",
                    prompt=f"Tôi đang yếu {stat.label} (mastery {skills.percent(stat.mastery)}). Hãy tạo 5 câu luyện Part 5 mới nhắm đúng các bẫy tôi hay sai và lưu vào ngân hàng câu luyện của tôi.",
                ))
        vocab_errors = (
            db.query(ErrorLog).filter(ErrorLog.user_id == user_id, ErrorLog.error_type == "VOCAB", error_log_service.open_filter()).count()
        )
        if vocab_errors >= 2:
            items.append(_suggestion(
                "vocab_from_errors", f"Nạp từ vựng từ {vocab_errors} câu sai VOCAB",
                "AI trích các từ/collocation khiến bạn sai và thêm vào Sổ tay SRS (tự bỏ qua từ đã có).",
                60, "mentor", "Nhờ AI nạp từ",
                prompt="Hãy xem các câu tôi sai mã VOCAB trong Sổ lỗi, trích những từ/collocation then chốt và thêm vào Sổ tay từ vựng của tôi (bỏ qua từ đã có).",
            ))
        leeches = skills.leech_cards(db, user_id)
        if leeches:
            words = ", ".join(card["word"] for card in leeches[:5])
            items.append(_suggestion(
                "leeches", f"{len(leeches)} thẻ hay quên: {words}",
                "AI viết lại ví dụ, thêm mẹo nhớ và collocation cho các thẻ bạn quên nhiều lần.",
                55, "mentor", "Nhờ AI làm thẻ dễ nhớ hơn",
                prompt=f"Các thẻ tôi hay quên: {words}. Hãy sửa từng thẻ với câu ví dụ mới dễ nhớ hơn, collocation và mẹo nhớ ngắn.",
            ))

    part5 = report.parts.get("Part 5")
    if part5 and part5.attempts >= 10 and part5.avg_time_seconds and part5.avg_time_seconds > 35:
        items.append(_suggestion(
            "speed_part5", f"Part 5 đang mất {round(part5.avg_time_seconds)}s/câu",
            "Mục tiêu ≤ 22s/câu để dư thời gian cho Part 7. Luyện chế độ thi thật bấm giờ.",
            58, "link", "Luyện tốc độ", href="/mock-tests?mode=exam&part=Part%205",
        ))

    roadmap = insights.get_roadmap(db, user_id)
    prediction = skills.predict_score(report, user)
    for task_id, evidence in list(planner.milestone_evidence(db, user_id, roadmap, report, prediction).items())[:2]:
        task = next((t for t in roadmap.tasks if t.id == task_id), None)
        if task is not None:
            items.append(_suggestion(
                f"milestone_{task_id}", f"Đủ điều kiện hoàn thành mốc: {task.title[:60]}", evidence,
                62, "tool", "Đánh dấu hoàn thành", tool="set_roadmap_task", args={"task_id": task_id, "is_completed": True},
            ))

    has_reminder = db.query(StudyReminder).filter(StudyReminder.user_id == user_id, StudyReminder.is_active.is_(True)).count() > 0
    if not has_reminder:
        items.append(_suggestion(
            "reminder", "Đặt lịch nhắc học 21:00",
            "Học đều mỗi ngày quan trọng hơn học dồn. Nhắc qua Telegram khi đã cấu hình bot.",
            30, "tool", "Đặt nhắc 21:00", tool="schedule_study_reminder",
            args={"scheduled_time": "21:00", "message": "Đến giờ học TOEIC: ôn thẻ SRS và làm nhiệm vụ hôm nay!"},
        ))

    yesterday = today - timedelta(days=1)
    minutes = activity.seconds_by_day(db, user_id, yesterday)
    if (report.total_attempts or db.query(Flashcard).count()) and minutes.get(yesterday, 0) < 60 and minutes.get(today, 0) < 60 \
            and yesterday.weekday() in settings.study_days and user.onboarded_at is not None:
        items.append(_suggestion(
            "comeback", "Quay lại với 10 phút hôm nay",
            "Hôm qua bạn chưa học. Chỉ cần làm nhiệm vụ đầu tiên trong kế hoạch để giữ nhịp.", 40, "link", "Xem kế hoạch", href="/",
        ))

    items.sort(key=lambda s: -s["priority"])
    return items[:limit]


def top_lines(db: Session, user_id: int, ai_online: bool, limit: int = 3, report=None) -> list:
    return [f"{s['title']} — {s['detail']}" for s in suggestions(db, user_id, ai_online, limit=limit, report=report)]


def by_id(db: Session, user_id: int, suggestion_id: str, ai_online: bool = True) -> Optional[dict]:
    return next((s for s in suggestions(db, user_id, ai_online, limit=50) if s["id"] == suggestion_id), None)
