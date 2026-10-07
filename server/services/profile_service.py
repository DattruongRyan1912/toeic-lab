"""Learner profile: validation, serialization and side effects (roadmap rescale + replan).

Used by /api/users/me, /api/learner/profile, onboarding and the AI tool update_learner_profile,
so every path applies the same rules.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from server.models import User
from server.services import insights, planner, scoring
from server.utils import timeutil

EXPLANATION_STYLES = {
    "concise": "Ngắn gọn: đáp án + quy tắc cốt lõi + 1 cặp paraphrase, tối đa ~8 dòng.",
    "detailed": "Chi tiết: phân tích 3 chiều đầy đủ, ví dụ thêm, bảng paraphrase/collocation.",
    "socratic": "Gợi mở: đặt câu hỏi dẫn dắt để học viên tự tìm ra đáp án trước khi giải thích.",
}
PARTS = ("Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6", "Part 7")
WEEKDAY_ALIASES = {
    "t2": 0, "thu2": 0, "mon": 0, "monday": 0,
    "t3": 1, "thu3": 1, "tue": 1, "tuesday": 1,
    "t4": 2, "thu4": 2, "wed": 2, "wednesday": 2,
    "t5": 3, "thu5": 3, "thu": 3, "thursday": 3,
    "t6": 4, "thu6": 4, "fri": 4, "friday": 4,
    "t7": 5, "thu7": 5, "sat": 5, "saturday": 5,
    "cn": 6, "chunhat": 6, "sun": 6, "sunday": 6,
}
# Changing any of these changes what the planner should schedule.
PLAN_FIELDS = {"daily_goal_minutes", "exam_date", "study_days", "new_cards_per_day", "focus_parts", "target_score",
               "baseline_listening", "baseline_reading", "auto_adjust"}
EDITABLE = ("display_name", "headline", "target_score", "daily_goal_minutes", "exam_date", "baseline_listening",
            "baseline_reading", "study_days", "new_cards_per_day", "explanation_style", "focus_parts",
            "learning_goal_note", "auto_adjust")


class ProfileError(ValueError):
    pass


def _weekday(value) -> int:
    if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
        day = int(value)
        if 0 <= day <= 6:
            return day
        raise ProfileError("Ngày học trong tuần phải từ 0 (T2) đến 6 (CN)")
    key = re.sub(r"[^a-z0-9]", "", str(value).lower().replace("ứ", "u").replace("ủ", "u").replace("ậ", "a"))
    if key in WEEKDAY_ALIASES:
        return WEEKDAY_ALIASES[key]
    raise ProfileError(f"Không hiểu ngày học '{value}' (dùng T2..T7, CN)")


def _parts(value) -> str:
    items = value.split(",") if isinstance(value, str) else list(value or [])
    parts = []
    for item in items:
        match = re.search(r"([1-7])", str(item))
        if match:
            part = f"Part {match.group(1)}"
            if part not in parts:
                parts.append(part)
    return ",".join(parts)


def normalize(changes: dict) -> dict:
    """Validate and convert raw values (REST payload or LLM tool args) into column values."""
    clean: dict = {}
    for key, value in changes.items():
        if key not in EDITABLE:
            continue
        if key in ("display_name", "headline"):
            clean[key] = (str(value or "").strip()[:100]) or None
        elif key == "learning_goal_note":
            clean[key] = (str(value or "").strip()[:2000]) or None
        elif key == "target_score":
            score = int(value)
            if not 10 <= score <= 990:
                raise ProfileError("Điểm mục tiêu phải trong khoảng 10-990")
            clean[key] = score
        elif key == "daily_goal_minutes":
            minutes = int(value)
            if not 10 <= minutes <= 600:
                raise ProfileError("Thời lượng mỗi ngày phải từ 10 đến 600 phút")
            clean[key] = minutes
        elif key in ("baseline_listening", "baseline_reading"):
            if value in (None, ""):
                clean[key] = None
            else:
                score = int(value)
                if not 5 <= score <= 495:
                    raise ProfileError("Điểm đầu vào mỗi kỹ năng phải trong khoảng 5-495")
                clean[key] = score
        elif key == "new_cards_per_day":
            if value in (None, ""):
                clean[key] = None
            else:
                cards = int(value)
                if not 0 <= cards <= 100:
                    raise ProfileError("Số thẻ mới mỗi ngày phải từ 0 đến 100")
                clean[key] = cards
        elif key == "exam_date":
            if value in (None, ""):
                clean[key] = None
            else:
                day = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
                if day < timeutil.local_today():
                    raise ProfileError("Ngày thi phải từ hôm nay trở đi")
                clean[key] = day
        elif key == "study_days":
            items = value.split(",") if isinstance(value, str) else list(value or [])
            days = sorted({_weekday(item) for item in items if str(item).strip() != ""})
            if not days:
                raise ProfileError("Cần ít nhất 1 ngày học trong tuần")
            clean[key] = ",".join(str(d) for d in days)
        elif key == "explanation_style":
            if value in (None, ""):
                clean[key] = None
            elif value not in EXPLANATION_STYLES:
                raise ProfileError("Phong cách giải thích: concise | detailed | socratic")
            else:
                clean[key] = value
        elif key == "focus_parts":
            clean[key] = _parts(value) or None
        elif key == "auto_adjust":
            clean[key] = None if value is None else bool(value)
    return clean


def apply(db: Session, user: User, changes: dict, *, replan: bool = True) -> dict:
    """Apply already-normalized changes. Returns {field: old_value} for fields that actually changed.

    Rescales the roadmap when the exam date changes and rebuilds the plan when planning inputs change.
    """
    old = {}
    for key, value in changes.items():
        if getattr(user, key) != value:
            old[key] = getattr(user, key)
            setattr(user, key, value)
    if not old:
        return old
    if "exam_date" in old or "target_score" in old:
        planner.rescale_roadmap(db, user)
    db.commit()
    if replan and PLAN_FIELDS & old.keys():
        planner.ensure_plan(db, user.id, force=True)
    return old


def serialize(user: User) -> dict:
    _, cefr, _ = scoring.cefr_for(user.target_score or 800)
    settings = planner.learner_settings(user)
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "headline": user.headline,
        "target_score": user.target_score or 800,
        "target_cefr": cefr,
        "daily_goal_minutes": user.daily_goal_minutes or 60,
        "created_at": user.created_at,
        "exam_date": user.exam_date,
        "days_to_exam": planner.days_to_exam(settings),
        "baseline_listening": user.baseline_listening,
        "baseline_reading": user.baseline_reading,
        "study_days": list(settings.study_days),
        "new_cards_per_day": user.new_cards_per_day,
        "effective_new_cards_per_day": settings.new_cards_per_day,
        "explanation_style": user.explanation_style or "detailed",
        "focus_parts": list(settings.focus_parts),
        "learning_goal_note": user.learning_goal_note,
        "auto_adjust": bool(user.auto_adjust) if user.auto_adjust is not None else True,
        "onboarded": user.onboarded_at is not None,
        "onboarded_at": user.onboarded_at,
    }


def style_instruction(user: Optional[User]) -> str:
    style = (user.explanation_style if user is not None else None) or "detailed"
    return EXPLANATION_STYLES.get(style, EXPLANATION_STYLES["detailed"])


def get_user(db: Session, user_id: int) -> User:
    return insights.get_or_create_user(db, user_id)
