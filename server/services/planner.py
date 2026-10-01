"""Adaptive study planner.

A rolling 7-day plan built from:
  * the learner's time budget (minutes/day) and study days,
  * SRS cards falling due + the daily new-card quota,
  * mistakes whose spaced review falls due,
  * skill mastery (weakest syntax lessons first, boosted by open errors and current roadmap milestones),
  * the exam date (more timed mock tests close to the exam, no new lessons in the last days).

Activity-based items (SRS, error review, lesson, practice, mock, smart, listening) complete themselves:
their status is derived from tracked activity when read. Manual marks (done / skipped) always win.
The plan regenerates once per day (and on demand); items created by the learner or the AI are kept.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Optional
from urllib.parse import quote

from sqlalchemy.orm import Session

from server import config
from server.models import (
    ErrorLog,
    Flashcard,
    LessonProgress,
    QuestionAttempt,
    SRSReviewLog,
    StudyPlanItem,
    User,
    UserCardSRS,
    UserTestSubmission,
)
from server.services import activity, curriculum, error_log_service, insights
from server.services import skills as skills_service
from server.utils import timeutil

WEEKDAYS = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")
DEFAULT_STUDY_DAYS = (0, 1, 2, 3, 4, 5)
PLAN_DAYS = 7
MIN_PER_CARD = 0.2       # a due review (~12s)
MIN_PER_NEW_CARD = 0.75  # a new card incl. its same-day learning steps, audio and example (~45s)
MIN_PER_ERROR_REVIEW = 1.5
MIN_PER_QUESTION = 0.75
LESSON_READING_MINUTES = 12
MOCK_MINUTES = 20
LISTENING_MINUTES = 15

AUTO_KINDS = {"srs", "error_review", "lesson", "practice", "smart", "mock", "listening"}
MANUAL_KINDS = {"custom", "ai_generate"}
KIND_TAGS = {
    "srs": "SRS",
    "error_review": "Ôn lỗi",
    "lesson": "Cú pháp",
    "practice": "Luyện đề",
    "smart": "Thông minh",
    "mock": "Thi thử",
    "listening": "Listening",
    "ai_generate": "AI",
    "custom": "Tự đặt",
}


@dataclass
class Settings:
    daily_minutes: int
    study_days: tuple
    new_cards_per_day: int
    exam_date: Optional[date]
    target_score: int
    focus_parts: tuple
    goal_minutes: int = 0  # the learner's own goal; daily_minutes may be lighter (auto_adjust)
    adjustments: tuple = field(default_factory=tuple)


BEHIND_COMPLETION = 0.5
BEHIND_MIN_ITEMS = 3
BEHIND_BUDGET_FACTOR = 0.75


@dataclass
class Focus:
    lesson_number: int
    title: str
    mastery: float
    status: str
    attempts: int
    open_errors: int
    question_count: int
    unseen: int
    viewed: bool
    score: float
    reason: str


# --------------------------------------------------------------------------- settings
def parse_study_days(value) -> tuple:
    if value is None or value == "":
        return DEFAULT_STUDY_DAYS
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
    else:
        parts = list(value)
    days = sorted({int(p) for p in parts if str(p).isdigit() and 0 <= int(p) <= 6})
    return tuple(days) or DEFAULT_STUDY_DAYS


def learner_settings(user: User) -> Settings:
    focus = tuple(p.strip() for p in (user.focus_parts or "").split(",") if p.strip())
    minutes = max(10, min(600, int(user.daily_goal_minutes or 60)))
    return Settings(
        daily_minutes=minutes,
        goal_minutes=minutes,
        study_days=parse_study_days(user.study_days),
        new_cards_per_day=insights.new_cards_per_day(user),
        exam_date=user.exam_date,
        target_score=int(user.target_score or 800),
        focus_parts=focus,
    )


def recent_completion(db: Session, user_id: int, days: int = 7) -> tuple:
    """(done, planned) plan items over the last `days` days (skipped items excluded)."""
    today = timeutil.local_today()
    past = [i for i in list_items(db, user_id, today - timedelta(days=days), today) if i["status"] != "skipped"]
    return sum(1 for i in past if i["status"] == "done"), len(past)


def is_behind(done: int, planned: int) -> bool:
    return planned >= BEHIND_MIN_ITEMS and done / planned < BEHIND_COMPLETION


def adapted_settings(db: Session, user: User) -> Settings:
    """auto_adjust (default on): a lighter plan while the learner is behind. Never raises the load by itself."""
    settings = learner_settings(user)
    if user.auto_adjust is False:
        return settings
    done, planned = recent_completion(db, user.id)
    if not is_behind(done, planned):
        return settings
    minutes = max(15, round(settings.daily_minutes * BEHIND_BUDGET_FACTOR))
    if minutes >= settings.daily_minutes:
        return settings
    note = f"7 ngày qua hoàn thành {done}/{planned} nhiệm vụ → kế hoạch nhẹ hơn: {minutes}/{settings.daily_minutes} phút/ngày"
    return replace(settings, daily_minutes=minutes, adjustments=(note,))


def days_to_exam(settings: Settings, day: Optional[date] = None) -> Optional[int]:
    if not settings.exam_date:
        return None
    return (settings.exam_date - (day or timeutil.local_today())).days


# --------------------------------------------------------------------------- forecasts
def srs_due_by_day(db: Session, user_id: int, start: date, days: int) -> Counter:
    end_utc = timeutil.local_day_start_utc(start + timedelta(days=days))
    counts: Counter = Counter()
    rows = (
        db.query(UserCardSRS.next_review_at)
        .join(Flashcard, Flashcard.id == UserCardSRS.card_id)
        .filter(UserCardSRS.user_id == user_id, UserCardSRS.state != "new", UserCardSRS.next_review_at < end_utc)
    )
    for (due_at,) in rows:
        counts[max(timeutil.local_date_of(due_at), start)] += 1  # overdue cards land on the first day
    return counts


def error_reviews_by_day(db: Session, user_id: int, start: date, days: int) -> Counter:
    end_utc = timeutil.local_day_start_utc(start + timedelta(days=days))
    counts: Counter = Counter()
    rows = db.query(ErrorLog.next_review_at).filter(
        ErrorLog.user_id == user_id, ErrorLog.question_id.isnot(None), error_log_service.open_filter()
    )
    for (due_at,) in rows:
        if due_at is None:
            counts[start] += 1
        elif due_at < end_utc:
            counts[max(timeutil.local_date_of(due_at), start)] += 1
    return counts


# --------------------------------------------------------------------------- focus selection
def milestone_lessons(roadmap) -> dict:
    """lesson_number -> week of pending roadmap tasks due this week or next."""
    if roadmap is None:
        return {}
    week = insights.current_week(roadmap)
    lessons = {}
    for task in roadmap.tasks:
        if task.is_completed or task.week_number > week + 1:
            continue
        for number in curriculum.lesson_numbers_in(task.title):
            lessons.setdefault(number, task.week_number)
    return lessons


def focus_lessons(db: Session, user_id: int, report, roadmap=None, limit: int = 3) -> list:
    titles = insights.lesson_titles(db)
    if not titles:
        return []
    progress = {p.lesson_number: p for p in db.query(LessonProgress).filter(LessonProgress.user_id == user_id)}
    milestones = milestone_lessons(roadmap)
    candidates = []
    for number, title in titles.items():
        stat = report.lessons.get(number)
        if stat is None:
            continue
        lp = progress.get(number)
        viewed = bool(lp and ((lp.time_spent_seconds or 0) >= 60 or lp.completed_at))
        score = (1 - stat.mastery) * 2 + min(stat.open_errors, 5) * 0.35
        reasons = []
        if stat.attempts:
            reasons.append(f"Mastery {skills_service.percent(stat.mastery)} sau {stat.attempts} câu")
        else:
            score += 0.4
            reasons.append("Chưa luyện chuyên đề này")
        if stat.open_errors:
            reasons.append(f"{stat.open_errors} lỗi chưa khắc phục")
        if number in milestones:
            score += 0.6
            reasons.append(f"Theo lộ trình tuần {milestones[number]}")
        if stat.trend is not None and stat.trend < -0.1:
            score += 0.3
            reasons.append("Đang giảm phong độ")
        if stat.status == "strong":
            score -= 1.0
        candidates.append(
            Focus(
                lesson_number=number, title=title, mastery=stat.mastery, status=stat.status, attempts=stat.attempts,
                open_errors=stat.open_errors, question_count=stat.question_count, unseen=stat.unseen_questions,
                viewed=viewed, score=round(score, 3), reason=" • ".join(reasons),
            )
        )
    candidates.sort(key=lambda f: (-f.score, f.lesson_number))
    return candidates[:limit]


def short_title(title: str) -> str:
    """'Bài 02: Liên Từ vs Giới Từ (...)' -> 'Bài 02'."""
    match = re.match(r"(Bài\s*\d+)", title or "")
    return match.group(1) if match else title


# --------------------------------------------------------------------------- generation
def _day_items(day: date, index: int, settings: Settings, focus: list, srs_due: Counter, err_due: Counter, report,
               pool: dict) -> list:
    budget = settings.daily_minutes
    remaining = budget
    items: list = []

    def add(kind: str, title: str, minutes: int, **extra) -> None:
        nonlocal remaining
        minutes = max(1, int(minutes))
        items.append(
            StudyPlanItem(
                plan_date=day, kind=kind, title=title, estimated_minutes=minutes, sort_order=len(items),
                status="pending", source="planner", **extra,
            )
        )
        remaining -= minutes

    to_exam = days_to_exam(settings, day)
    exam_mode = to_exam is not None and to_exam <= 14
    final_days = to_exam is not None and to_exam <= 3

    # 1) SRS: reviews due + new cards, capped at 40% of the budget (new cards give way first)
    reviews = srs_due.get(day, 0)
    quota = pool["new_today"] if index == 0 else settings.new_cards_per_day
    new_cards = 0 if final_days else min(quota, pool["new_cards"])
    cap = max(5, int(budget * 0.4))
    if reviews * MIN_PER_CARD + new_cards * MIN_PER_NEW_CARD > cap:  # new cards give way first
        new_cards = max(0, int((cap - reviews * MIN_PER_CARD) / MIN_PER_NEW_CARD))
    pool["new_cards"] -= new_cards
    cards = reviews + new_cards
    if cards:
        reason = "Ôn đúng hạn để giữ trí nhớ dài hạn (SM-2)" if reviews else "Nạp từ vựng mới theo hạn mức mỗi ngày của bạn"
        if new_cards < min(settings.new_cards_per_day, quota) and pool["new_cards"] > 0 and not final_days:
            reason += f"; giảm thẻ mới còn {new_cards} để vừa {budget} phút/ngày"
        title = (
            f"Ôn {reviews} thẻ + học {new_cards} thẻ mới" if reviews and new_cards
            else f"Học {new_cards} thẻ từ vựng mới" if new_cards else f"Ôn {reviews} thẻ từ vựng"
        )
        add(
            "srs", title, max(1, math.ceil(reviews * MIN_PER_CARD + new_cards * MIN_PER_NEW_CARD)), target_count=cards,
            detail=f"{reviews} thẻ đến hạn + {new_cards} thẻ mới", reason=reason, priority=3,
        )

    # 2) Mistakes due for spaced review
    due = err_due.get(day, 0)
    if due:
        count = min(due, max(3, int(budget * 0.3 / MIN_PER_ERROR_REVIEW)))
        add(
            "error_review", f"Ôn lại {count} câu sai đến hạn", math.ceil(count * MIN_PER_ERROR_REVIEW), target_count=count,
            detail="Làm lại câu đã sai — đúng 3 lần cách nhau 1-3-7 ngày thì tự chuyển 'Đã nắm chắc'",
            reason=f"{due} câu sai đến lịch ôn", priority=3,
        )

    # 3) Timed mock tests close to the exam
    if exam_mode and remaining >= 15 and (final_days or index % 2 == 0):
        add(
            "mock", "Thi thử Part 5 bấm giờ", min(MOCK_MINUTES, remaining), part="Part 5", target_count=1,
            reason=f"Còn {to_exam} ngày đến kỳ thi: luyện áp lực thời gian thật", priority=2,
        )

    # 4) Focus lesson of the day (rotates through the weakest lessons)
    if focus and remaining >= 6 and not final_days:
        pick = focus[index % len(focus)]
        name = short_title(pick.title)
        if not pick.viewed and not exam_mode and remaining >= 15:
            add("lesson", f"Học {pick.title}", min(LESSON_READING_MINUTES, remaining - 5), lesson_number=pick.lesson_number,
                reason=pick.reason, priority=2)
        if pick.question_count and remaining >= 4:
            count = min(pick.question_count, 15, max(3, int(remaining / MIN_PER_QUESTION)))
            add(
                "practice", f"Luyện {count} câu {name}", math.ceil(count * MIN_PER_QUESTION), lesson_number=pick.lesson_number,
                part="Part 5", target_count=count, reason=pick.reason, priority=2,
            )
        if (pool.get("ai_online") and pick.lesson_number not in pool["ai_lessons"]
                and pick.unseen < 3 and pick.status in ("weak", "improving", "not_started") and pick.question_count < 12):
            pool["ai_lessons"].add(pick.lesson_number)  # one AI request per lesson per plan
            prompt = (
                f"Tạo 5 câu luyện Part 5 mới cho {pick.title}, nhắm đúng các bẫy tôi hay sai, "
                "rồi lưu vào ngân hàng câu luyện của tôi."
            )
            items.append(
                StudyPlanItem(
                    plan_date=day, kind="ai_generate", title=f"Nhờ AI tạo thêm câu luyện {name}", estimated_minutes=2,
                    sort_order=len(items), status="pending", source="planner", lesson_number=pick.lesson_number,
                    detail=prompt, reason=f"Ngân hàng đề chỉ còn {pick.unseen} câu chưa làm cho chuyên đề này", priority=1,
                )
            )

    # 5) Fill the remaining budget: listening drill, smart mixed set, then a second focus lesson
    listening, reading = report.sections.get("listening"), report.sections.get("reading")
    listening_first = listening is None or listening.attempts < 5 or (reading is not None and listening.mastery <= reading.mastery)
    if ("Part 7" in settings.focus_parts or "Part 5" in settings.focus_parts) and index % 2 == 0:
        listening_first = False  # reading-focused learners alternate
    options = ["listening", "smart"] if listening_first or pool["bank_total"] < 5 else ["smart", "listening"]
    if len(focus) > 1 and not final_days:
        options.append("second_focus")
    first_pick = focus[index % len(focus)].lesson_number if focus else None
    for option in options:
        if remaining < 8:
            break
        if option == "listening":
            add(
                "listening", "Dictation & Shadowing Part 2-3", min(LISTENING_MINUTES, remaining),
                detail="Bấm 'Bắt đầu' để tính giờ: chép chính tả 10 câu Part 2, shadowing 1 đoạn Part 3",
                reason="Listening chưa có đủ dữ liệu luyện trong app" if listening is None or listening.attempts < 5 else "Listening đang yếu hơn Reading",
                priority=1,
            )
        elif option == "smart" and pool["bank_total"] >= 5:
            count = min(pool["bank_total"], 15, max(5, int(remaining / MIN_PER_QUESTION)))
            add(
                "smart", f"Luyện thông minh {count} câu", math.ceil(count * MIN_PER_QUESTION), target_count=count,
                reason="Trộn câu sai đến hạn, chuyên đề yếu và câu mới", priority=1,
            )
        elif option == "second_focus":
            second = focus[(index + 1) % len(focus)]
            if second.lesson_number != first_pick and second.question_count:
                count = min(second.question_count, 10, max(3, int(remaining / MIN_PER_QUESTION)))
                add(
                    "practice", f"Luyện {count} câu {short_title(second.title)}", math.ceil(count * MIN_PER_QUESTION),
                    lesson_number=second.lesson_number, part="Part 5", target_count=count, reason=second.reason, priority=1,
                )
    return items


def _ai_online() -> bool:
    from server.services import ai_agent_service  # lazy: ai_agent_service → agent_tools → planner

    return not ai_agent_service.provider_status()["offline"]


def generate_plan(db: Session, user_id: int, start: Optional[date] = None, days: int = PLAN_DAYS, report=None) -> list:
    """(Re)build the plan for [start, start+days). Keeps manual marks and items added by the learner / AI."""
    user = insights.get_or_create_user(db, user_id)
    start = start or timeutil.local_today()
    settings = adapted_settings(db, user)
    report = report or skills_service.compute(db, user_id)
    roadmap = insights.get_roadmap(db, user_id)
    focus = focus_lessons(db, user_id, report, roadmap)
    srs_due = srs_due_by_day(db, user_id, start, days)
    err_due = error_reviews_by_day(db, user_id, start, days)
    end = start + timedelta(days=days)
    counts = insights.srs_counts(db, user_id)
    pool = {
        "new_cards": counts["new_total"],
        "new_today": counts["new_available"] if start == timeutil.local_today() else settings.new_cards_per_day,
        "bank_total": sum(stat.question_count for stat in report.parts.values()),
        "ai_online": _ai_online(),
        "ai_lessons": set(),
    }

    existing = (
        db.query(StudyPlanItem)
        .filter(StudyPlanItem.user_id == user_id, StudyPlanItem.plan_date >= start, StudyPlanItem.plan_date < end)
        .all()
    )
    kept = []
    for item in existing:
        if item.source == "planner" and (item.status or "pending") == "pending":
            db.delete(item)
        else:
            kept.append(item)
    kept_keys = {(i.plan_date, i.kind, i.lesson_number, i.part) for i in kept}

    created, index = [], 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        if settings.exam_date and day > settings.exam_date:
            break
        if day.weekday() not in settings.study_days:
            continue
        for item in _day_items(day, index, settings, focus, srs_due, err_due, report, pool):
            if (item.plan_date, item.kind, item.lesson_number, item.part) in kept_keys:
                continue
            item.user_id = user_id
            db.add(item)
            created.append(item)
        index += 1
    user.plan_generated_on = timeutil.local_today()
    db.commit()
    return created


def ensure_plan(db: Session, user_id: int, report=None, force: bool = False) -> bool:
    """Regenerate once per local day (or when forced). Returns True when a new plan was built."""
    user = insights.get_or_create_user(db, user_id)
    if force or user.plan_generated_on != timeutil.local_today():
        generate_plan(db, user_id, report=report)
        return True
    return False


# --------------------------------------------------------------------------- progress (derived)
def _href(item: StudyPlanItem) -> str:
    kind = item.kind
    if kind == "srs":
        return "/vocab"
    if kind == "error_review":
        return "/mock-tests?mode=review"
    if kind == "lesson":
        return f"/lessons?lesson={item.lesson_number}"
    if kind == "practice":
        return f"/mock-tests?lesson={item.lesson_number}" if item.lesson_number else f"/mock-tests?part={quote(item.part or 'Part 5')}"
    if kind == "smart":
        return "/mock-tests?mode=smart"
    if kind == "mock":
        return f"/mock-tests?mode=exam&part={quote(item.part or 'Part 5')}"
    if kind == "ai_generate":
        return f"/mentor?prompt={quote(item.detail or item.title)}"
    if kind == "listening":
        return "/listening"
    return "/roadmaps"


def derive_progress(db: Session, user_id: int, items: list) -> dict:
    """item.id -> (progress, done) computed from tracked activity on the item's day."""
    auto = [i for i in items if i.kind in AUTO_KINDS]
    if not auto:
        return {}
    start = min(i.plan_date for i in auto)
    end = max(i.plan_date for i in auto) + timedelta(days=1)
    since, until = timeutil.local_day_start_utc(start), timeutil.local_day_start_utc(end)

    srs = Counter(
        timeutil.local_date_of(ts)
        for (ts,) in db.query(SRSReviewLog.reviewed_at).filter(
            SRSReviewLog.user_id == user_id, SRSReviewLog.reviewed_at >= since, SRSReviewLog.reviewed_at < until
        )
    )
    by_lesson, by_part, by_mode = Counter(), Counter(), Counter()
    for created_at, lesson, part, mode in db.query(
        QuestionAttempt.created_at, QuestionAttempt.lesson_number, QuestionAttempt.part, QuestionAttempt.mode
    ).filter(QuestionAttempt.user_id == user_id, QuestionAttempt.created_at >= since, QuestionAttempt.created_at < until):
        day = timeutil.local_date_of(created_at)
        by_lesson[(day, lesson)] += 1
        by_part[(day, part)] += 1
        by_mode[(day, mode)] += 1
    exams = Counter(
        timeutil.local_date_of(ts)
        for (ts,) in db.query(UserTestSubmission.submitted_at).filter(
            UserTestSubmission.user_id == user_id, UserTestSubmission.mode == "exam",
            UserTestSubmission.submitted_at >= since, UserTestSubmission.submitted_at < until,
        )
    )
    reviewed_logs = Counter(
        timeutil.local_date_of(ts)
        for (ts,) in db.query(ErrorLog.last_reviewed_at).filter(
            ErrorLog.user_id == user_id, ErrorLog.last_reviewed_at >= since, ErrorLog.last_reviewed_at < until
        )
    )
    seconds = activity.seconds_by_day_and_kind(db, user_id, start, end)
    completed_lessons = {
        (timeutil.local_date_of(p.completed_at), p.lesson_number)
        for p in db.query(LessonProgress).filter(LessonProgress.user_id == user_id, LessonProgress.completed_at.isnot(None))
    }

    progress = {}
    for item in auto:
        day, target = item.plan_date, item.target_count or 0
        if item.kind == "srs":
            value = srs[day]
            done = value >= target > 0
        elif item.kind == "error_review":
            value = max(by_mode[(day, "review")], reviewed_logs[day])  # reviews done in any mode count
            done = value >= target > 0
        elif item.kind == "lesson":
            value = round(seconds.get((day, "lesson", f"lesson:{item.lesson_number}"), 0) / 60)
            done = value >= min(8, item.estimated_minutes or 8) or (day, item.lesson_number) in completed_lessons
        elif item.kind == "practice":
            value = by_lesson[(day, item.lesson_number)] if item.lesson_number else by_part[(day, item.part)]
            done = value >= target > 0
        elif item.kind == "smart":
            value = by_mode[(day, "smart")]
            done = value >= target > 0
        elif item.kind == "mock":
            value = exams[day]
            done = value >= 1
        else:  # listening
            value = round(sum(v for (d, kind, _ref), v in seconds.items() if d == day and kind == "listening") / 60)
            done = value >= max(1, round((item.estimated_minutes or LISTENING_MINUTES) * 0.8))
        progress[item.id] = (value, done)
    return progress


def serialize_item(item: StudyPlanItem, derived: Optional[tuple]) -> dict:
    stored = item.status or "pending"
    if stored in ("done", "skipped"):
        status, auto = stored, False
    elif derived is not None:
        status, auto = ("done" if derived[1] else "pending"), True
    else:
        status, auto = stored, False
    return {
        "id": item.id,
        "date": item.plan_date,
        "kind": item.kind,
        "tag": KIND_TAGS.get(item.kind, item.kind),
        "title": item.title,
        "detail": item.detail,
        "reason": item.reason,
        "lesson_number": item.lesson_number,
        "part": item.part,
        "target_count": item.target_count,
        "progress": derived[0] if derived is not None else None,
        "estimated_minutes": item.estimated_minutes or 0,
        "priority": item.priority or 0,
        "status": status,
        "auto": auto,
        "source": item.source or "planner",
        "href": _href(item),
        "ref": item.ref,
    }


def list_items(db: Session, user_id: int, start: date, end: date) -> list:
    items = (
        db.query(StudyPlanItem)
        .filter(StudyPlanItem.user_id == user_id, StudyPlanItem.plan_date >= start, StudyPlanItem.plan_date < end)
        .order_by(StudyPlanItem.plan_date.asc(), StudyPlanItem.sort_order.asc(), StudyPlanItem.id.asc())
        .all()
    )
    progress = derive_progress(db, user_id, items)
    return [serialize_item(item, progress.get(item.id)) for item in items]


def items_for_day(db: Session, user_id: int, day: Optional[date] = None) -> list:
    day = day or timeutil.local_today()
    return list_items(db, user_id, day, day + timedelta(days=1))


def week_view(db: Session, user_id: int, report=None) -> dict:
    ensure_plan(db, user_id, report=report)
    user = insights.get_or_create_user(db, user_id)
    settings = adapted_settings(db, user)
    report = report or skills_service.compute(db, user_id)
    today = timeutil.local_today()
    end = today + timedelta(days=PLAN_DAYS)
    items = list_items(db, user_id, today, end)
    studied = activity.seconds_by_day(db, user_id, today - timedelta(days=7), end)

    days = []
    for offset in range(PLAN_DAYS):
        day = today + timedelta(days=offset)
        day_items = [item for item in items if item["date"] == day]
        active = [item for item in day_items if item["status"] != "skipped"]
        days.append(
            {
                "date": day,
                "weekday": WEEKDAYS[day.weekday()],
                "is_today": offset == 0,
                "is_study_day": day.weekday() in settings.study_days,
                "planned_minutes": sum(item["estimated_minutes"] for item in active),
                "done_minutes": sum(item["estimated_minutes"] for item in active if item["status"] == "done"),
                "studied_minutes": round(studied.get(day, 0) / 60),
                "items": day_items,
            }
        )

    past = list_items(db, user_id, today - timedelta(days=7), today)
    planned_past = [item for item in past if item["status"] != "skipped"]
    done_past = [item for item in planned_past if item["status"] == "done"]
    studied_past = sum(studied.get(today - timedelta(days=d), 0) for d in range(1, 8))
    study_days_past = sum(1 for d in range(1, 8) if (today - timedelta(days=d)).weekday() in settings.study_days)
    completion = round(len(done_past) / len(planned_past), 3) if planned_past else None

    return {
        "start": today,
        "end": end - timedelta(days=1),
        "generated_on": user.plan_generated_on,
        "settings": {
            "daily_minutes": settings.goal_minutes,
            "planned_daily_minutes": settings.daily_minutes,
            "auto_adjust": user.auto_adjust is not False,
            "adjustments": list(settings.adjustments),
            "study_days": list(settings.study_days),
            "new_cards_per_day": settings.new_cards_per_day,
            "exam_date": settings.exam_date,
            "days_to_exam": days_to_exam(settings),
            "focus_parts": list(settings.focus_parts),
        },
        "focus": [
            {
                "lesson_number": f.lesson_number, "title": f.title, "mastery": round(f.mastery, 3), "status": f.status,
                "attempts": f.attempts, "open_errors": f.open_errors, "question_count": f.question_count, "reason": f.reason,
            }
            for f in focus_lessons(db, user_id, report, insights.get_roadmap(db, user_id))
        ],
        "days": days,
        "history": {
            "days": 7,
            "planned_items": len(planned_past),
            "done_items": len(done_past),
            "completion_rate": completion,
            "studied_minutes": round(studied_past / 60),
            "goal_minutes": settings.daily_minutes * study_days_past,
            "behind": is_behind(len(done_past), len(planned_past)),
        },
    }


# --------------------------------------------------------------------------- roadmap adaptation
def rescale_roadmap(db: Session, user: User) -> Optional[dict]:
    """Stretch/compress milestone weeks so the 24-week design ends at the exam date."""
    roadmap = insights.get_roadmap(db, user.id)
    if roadmap is None:
        return None
    base_total = roadmap.base_total_weeks or roadmap.total_weeks or 24
    roadmap.base_total_weeks = base_total
    start = insights.roadmap_start(roadmap)
    if user.exam_date and user.exam_date > start:
        total = max(2, min(52, math.ceil((user.exam_date - start).days / 7)))
    else:
        total = base_total
    roadmap.total_weeks = total
    for task in roadmap.tasks:
        base = task.base_week or task.week_number
        task.base_week = base
        task.week_number = max(1, min(total, math.ceil(base * total / base_total)))
    roadmap.current_week = insights.current_week(roadmap)
    db.flush()
    return {"total_weeks": total, "base_total_weeks": base_total}


_VOCAB_COUNT = re.compile(r"(\d{2,4})\s*(?:từ|thẻ)")
_SCORE = re.compile(r"\b(\d{3})\b")


def milestone_evidence(db: Session, user_id: int, roadmap, report, prediction: dict) -> dict:
    """task_id -> human-readable evidence that a pending milestone's goal is already met."""
    if roadmap is None:
        return {}
    learned = (
        db.query(UserCardSRS).filter(UserCardSRS.user_id == user_id, UserCardSRS.state != "new").count()
    )
    evidence = {}
    for task in roadmap.tasks:
        if task.is_completed:
            continue
        lessons = curriculum.lesson_numbers_in(task.title)
        if task.category == "Syntax" and lessons:
            stats = [report.lessons[n] for n in lessons if n in report.lessons]
            if stats and all(s.mastery >= 0.7 and s.attempts >= 3 for s in stats):
                evidence[task.id] = "Đạt: " + ", ".join(f"Bài {s.lesson_number:02d} {skills_service.percent(s.mastery)}" for s in stats)
        elif task.category == "Vocab":
            match = _VOCAB_COUNT.search(task.title)
            if match and learned >= int(match.group(1)):
                evidence[task.id] = f"Đã học {learned} thẻ ≥ {match.group(1)}"
        elif task.category == "Test":
            scores = [int(x) for x in _SCORE.findall(task.title) if 300 <= int(x) <= 990]
            expected = prediction["total"]["expected"]
            if scores and prediction["confidence"] >= 0.25 and expected >= min(scores):
                evidence[task.id] = f"Điểm dự đoán {expected} ≥ {min(scores)}"
    return evidence


def as_task(item: dict) -> dict:
    """Plan item -> the dashboard 'today task' shape."""
    detail = item["detail"]
    if item["progress"] is not None and item["target_count"]:
        detail = f"{item['progress']}/{item['target_count']} • {detail}" if detail else f"{item['progress']}/{item['target_count']}"
    return {
        "key": f"plan-{item['id']}",
        "plan_item_id": item["id"],
        "kind": item["kind"],
        "title": item["title"],
        "tag": item["tag"],
        "href": item["href"],
        "done": item["status"] == "done",
        "status": item["status"],
        "auto": item["auto"],
        "detail": detail,
        "reason": item["reason"],
        "estimated_minutes": item["estimated_minutes"],
        "progress": item["progress"],
        "target": item["target_count"],
        "lesson_number": item["lesson_number"],
    }


def default_new_cards() -> int:
    return config.SRS_NEW_CARDS_PER_DAY


def study_days_label(days) -> str:
    return ", ".join(WEEKDAYS[d] for d in parse_study_days(days))


def pending_count_by_day(items: list) -> dict:
    counts = defaultdict(int)
    for item in items:
        if item["status"] == "pending":
            counts[item["date"]] += 1
    return counts
