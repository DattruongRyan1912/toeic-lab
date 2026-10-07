"""Learning insights — the glue between modules.

SRS reviews, practice attempts, the error log, learning gaps, the adaptive plan, the roadmap and lessons
all feed into the functions below. The dashboard, the AI mentor (learner context), the offline mentor and
reminders read from the same place, so every screen shows the same numbers.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, case, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server import config
from server.models import (
    AILearningGap,
    AIMessage,
    ErrorLog,
    Flashcard,
    KnowledgeLesson,
    QuestionAttempt,
    Roadmap,
    SprintTask,
    SRSReviewLog,
    TestQuestion,
    User,
    UserCardSRS,
    UserTestSubmission,
)
from server.services import activity, curriculum, scoring
from server.utils import timeutil

WEEKDAY_LABELS = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")
ACTIVITY_KEYS = ("srs_reviews", "questions_answered", "errors_logged", "tasks_completed", "mentor_questions")


# --------------------------------------------------------------------------- users & roadmap
def get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        username = "learner" if user_id == config.DEFAULT_USER_ID else f"learner{user_id}"
        user = User(id=user_id, username=username, target_score=800, daily_goal_minutes=60)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def display_name(user: User) -> str:
    return user.display_name or user.username


def new_cards_per_day(user: Optional[User]) -> int:
    if user is not None and user.new_cards_per_day is not None:
        return max(0, int(user.new_cards_per_day))
    return config.SRS_NEW_CARDS_PER_DAY


def get_roadmap(db: Session, user_id: int) -> Optional[Roadmap]:
    return db.query(Roadmap).filter_by(user_id=user_id).order_by(Roadmap.id.asc()).first()


def roadmap_start(roadmap: Roadmap) -> date:
    return roadmap.start_date or timeutil.local_date_of(roadmap.created_at) or timeutil.local_today()


def current_week(roadmap: Roadmap, today: Optional[date] = None) -> int:
    today = today or timeutil.local_today()
    total = roadmap.total_weeks or 24
    elapsed = (today - roadmap_start(roadmap)).days
    week = elapsed // 7 + 1 if elapsed >= 0 else 1
    return max(1, min(total, week))


def phase_for_week(week: int, total_weeks: Optional[int]) -> int:
    span = max(1, round((total_weeks or 24) / 3))
    return max(1, min(3, (week - 1) // span + 1))


PHASE_INFO = {
    1: ("Xây nền cú pháp & từ vựng", "12 chuyên đề cú pháp Part 5, Dictation Part 1 & 2, thẻ SRS mỗi ngày."),
    2: ("Tăng tốc Part 3, 4, 6 & 7", "Shadowing Part 3 & 4, kỹ thuật 3-Pass Scanning cho Part 7."),
    3: ("Thực chiến đề ETS & bịt Sổ lỗi", "Full test 120 phút, chữa RCA triệt để, tâm lý phòng thi."),
}
_PART_MENTION = re.compile(r"Part\s*((?:\d\s*(?:,|&|-|và)?\s*)+)")
_CARD_COUNT = re.compile(r"(\d{2,4})\s*(?:từ|thẻ)")


def content_gaps(db: Session, tasks) -> dict:
    """task_id -> why the bank cannot support this milestone yet (missing parts, no full test, too few cards)."""
    parts = {part for (part,) in db.query(TestQuestion.part).distinct() if part}
    biggest_test = max((count for (_, count) in db.query(TestQuestion.test_id, func.count(TestQuestion.id)).group_by(TestQuestion.test_id)), default=0)
    cards = db.query(func.count(Flashcard.id)).scalar() or 0
    gaps = {}
    for task in tasks:
        title = task.title or ""
        wanted = {f"Part {d}" for match in _PART_MENTION.findall(title) for d in re.findall(r"\d", match)}
        if "Triple Passage" in title:
            wanted.add("Part 7")
        missing = sorted(wanted - parts)
        notes = [f"Chưa có đề {', '.join(missing)}"] if missing else []
        if ("Full Test" in title or "120 phút" in title) and biggest_test < 200:
            notes.append("Chưa có đề full 200 câu")
        count = _CARD_COUNT.search(title) if task.category == "Vocab" else None
        if count and int(count.group(1)) > cards:
            notes.append(f"Kho mới có {cards} thẻ")
        if notes:
            gaps[task.id] = "; ".join(notes)
    return gaps


def roadmap_phases(roadmap: Roadmap, start_score: Optional[int], target: int) -> list:
    """Phase cards: week ranges from the (rescaled) milestones themselves, score goals from the learner's own
    start (onboarding baseline) to target, so nothing on the page is a fixed number."""
    total = roadmap.total_weeks or 24
    numbers = sorted({task.phase or 1 for task in roadmap.tasks}) or [1, 2, 3]
    weeks = {n: [t.week_number for t in roadmap.tasks if (t.phase or 1) == n] for n in numbers}
    phases = []
    for index, number in enumerate(numbers):
        # A phase spans its own (rescaled) milestones up to the next phase's first one; after compressing a
        # roadmap two phases may share a boundary week rather than hide a milestone outside its phase.
        start = 1 if index == 0 else min(weeks[number], default=phases[-1]["end_week"] + 1)
        if index == len(numbers) - 1:
            end = total
        else:
            next_start = min(weeks[numbers[index + 1]], default=total)
            own_end = max(weeks[number], default=start)
            end = next_start - 1 if next_start > own_end else own_end
        title, focus = PHASE_INFO.get(number, (f"Giai đoạn {number}", ""))
        if start_score is not None and start_score < target:
            goal = int(round((start_score + (target - start_score) * (index + 1) / len(numbers)) / 5) * 5)
        else:
            goal = target if index == len(numbers) - 1 else None
        phases.append({"phase": number, "title": title, "focus": focus, "start_week": start, "end_week": max(start, end), "goal_score": goal})
    return phases


def learner_phases(roadmap: Roadmap) -> list:
    user = roadmap.user
    target = (user.target_score if user is not None else None) or 800
    has_baseline = user is not None and user.baseline_listening and user.baseline_reading
    return roadmap_phases(roadmap, user.baseline_listening + user.baseline_reading if has_baseline else None, target)


def phase_of_week(phases: list, week: int) -> int:
    return next((p["phase"] for p in phases if p["start_week"] <= week <= p["end_week"]), phases[-1]["phase"] if phases else 1)


def roadmap_progress(roadmap: Roadmap) -> tuple:
    total = len(roadmap.tasks)
    done = sum(1 for task in roadmap.tasks if task.is_completed)
    return done, total, round(done / total * 100) if total else 0


def serialize_roadmap(roadmap: Roadmap, evidence: Optional[dict] = None, gaps: Optional[dict] = None) -> dict:
    week = current_week(roadmap)
    done, total, percent = roadmap_progress(roadmap)
    evidence = evidence or {}
    gaps = gaps or {}
    user = roadmap.user
    phases = learner_phases(roadmap)
    return {
        "id": roadmap.id,
        "title": roadmap.title,
        "total_weeks": roadmap.total_weeks or 24,
        "base_total_weeks": roadmap.base_total_weeks or roadmap.total_weeks or 24,
        "current_week": week,
        "current_phase": phase_of_week(phases, week),
        "phases": phases,
        "start_date": roadmap_start(roadmap),
        "exam_date": user.exam_date if user is not None else None,
        "status": roadmap.status or "in_progress",
        "progress_percent": percent,
        "completed_tasks": done,
        "total_tasks": total,
        "tasks": [
            {
                "id": task.id,
                "phase": task.phase or 1,
                "week_number": task.week_number,
                "base_week": task.base_week or task.week_number,
                "category": task.category,
                "title": task.title,
                "is_completed": bool(task.is_completed),
                "completed_at": task.completed_at,
                "source": task.source or "seed",
                "auto_met": task.id in evidence,
                "evidence": evidence.get(task.id),
                "content_note": gaps.get(task.id),
            }
            for task in roadmap.tasks
        ],
    }


# --------------------------------------------------------------------------- SRS
def ensure_srs_records(db: Session, user_id: int) -> int:
    """Every flashcard must have an SRS row for the learner, otherwise it never shows up for review."""
    missing = (
        db.query(Flashcard.id)
        .outerjoin(UserCardSRS, and_(UserCardSRS.card_id == Flashcard.id, UserCardSRS.user_id == user_id))
        .filter(UserCardSRS.id.is_(None))
        .all()
    )
    if not missing:
        return 0
    now = timeutil.utcnow()
    for (card_id,) in missing:
        db.add(UserCardSRS(user_id=user_id, card_id=card_id, state="new", next_review_at=now))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # a parallel request (vocab page loads summary + due at once) inserted them first
        return 0
    return len(missing)


def srs_due_before() -> datetime:
    """A card is due today when its review falls before the next local midnight (same day boundary as the plan)."""
    return timeutil.local_day_start_utc(timeutil.local_today() + timedelta(days=1))


def srs_counts(db: Session, user_id: int, category: Optional[str] = None) -> dict:
    due_before = srs_due_before()
    day_start = timeutil.local_day_start_utc(timeutil.local_today())
    base = db.query(UserCardSRS).join(Flashcard, Flashcard.id == UserCardSRS.card_id).filter(UserCardSRS.user_id == user_id)
    if category and category != "all":
        base = base.filter(Flashcard.category == category)
    review_due = base.filter(UserCardSRS.state != "new", UserCardSRS.next_review_at < due_before).count()
    new_total = base.filter(UserCardSRS.state == "new").count()
    mastered = base.filter(UserCardSRS.state == "mastered").count()
    learning = base.filter(UserCardSRS.state.in_(("learning", "review"))).count()
    logs_today = db.query(SRSReviewLog).filter(SRSReviewLog.user_id == user_id, SRSReviewLog.reviewed_at >= day_start)
    reviewed_today = logs_today.count()
    new_introduced_today = logs_today.filter(SRSReviewLog.prev_state == "new").count()
    per_day = new_cards_per_day(db.get(User, user_id))
    new_available = min(new_total, max(0, per_day - new_introduced_today))
    return {
        "review_due": review_due,
        "new_total": new_total,
        "new_available": new_available,
        "mastered": mastered,
        "learning": learning,
        "reviewed_today": reviewed_today,
        "new_introduced_today": new_introduced_today,
        "new_cards_per_day": per_day,
        "session_size": review_due + new_available,
    }


def due_queue(
    db: Session,
    user_id: int,
    limit: int = 30,
    category: Optional[str] = None,
    mode: str = "srs",
) -> list:
    """Cards to study now:
    - mode="srs": overdue reviews first, then new cards within today's quota.
    - mode="all" or "cram": all cards in this category (or user-wide) prioritizing overdue, learning, then new.
    - mode="new": unlearned new cards only.
    """
    counts = srs_counts(db, user_id, category=category)
    due_before = srs_due_before()
    base = db.query(UserCardSRS).join(Flashcard, Flashcard.id == UserCardSRS.card_id).filter(UserCardSRS.user_id == user_id)
    if category and category != "all":
        base = base.filter(Flashcard.category == category)

    if mode in ("all", "cram"):
        return (
            base.order_by(
                case(
                    (and_(UserCardSRS.state != "new", UserCardSRS.next_review_at < due_before), 1),
                    (UserCardSRS.state.in_(("learning", "review")), 2),
                    (UserCardSRS.state == "new", 3),
                    else_=4,
                ),
                UserCardSRS.next_review_at.asc(),
                UserCardSRS.card_id.asc(),
            )
            .limit(limit)
            .all()
        )
    elif mode == "new":
        return base.filter(UserCardSRS.state == "new").order_by(UserCardSRS.card_id.asc()).limit(limit).all()

    reviews = (
        base.filter(UserCardSRS.state != "new", UserCardSRS.next_review_at < due_before)
        .order_by(UserCardSRS.next_review_at.asc())
        .limit(limit)
        .all()
    )
    new_cap = min(max(0, limit - len(reviews)), counts["new_available"])
    news = base.filter(UserCardSRS.state == "new").order_by(UserCardSRS.card_id.asc()).limit(new_cap).all() if new_cap else []
    return reviews + news


def category_stats(db: Session, user_id: int) -> list:
    due_before = srs_due_before()
    results = (
        db.query(
            Flashcard.category,
            func.count(Flashcard.id).label("total"),
            func.sum(case((and_(UserCardSRS.state != "new", UserCardSRS.next_review_at < due_before), 1), else_=0)).label("due"),
            func.sum(case((UserCardSRS.state == "mastered", 1), else_=0)).label("mastered"),
            func.sum(case((UserCardSRS.state.in_(("learning", "review")), 1), else_=0)).label("learning"),
            func.sum(case((UserCardSRS.state == "new", 1), else_=0)).label("new_cards"),
        )
        .outerjoin(UserCardSRS, and_(UserCardSRS.card_id == Flashcard.id, UserCardSRS.user_id == user_id))
        .group_by(Flashcard.category)
        .order_by(func.count(Flashcard.id).desc())
        .all()
    )
    return [
        {
            "category": row[0] or "General Business",
            "total": int(row[1] or 0),
            "due": int(row[2] or 0),
            "mastered": int(row[3] or 0),
            "learning": int(row[4] or 0),
            "new_cards": int(row[5] or 0),
        }
        for row in results
    ]


# --------------------------------------------------------------------------- activity & streak
def activity_by_date(db: Session, user_id: int, since_day: date) -> dict:
    since = timeutil.local_day_start_utc(since_day)
    buckets = defaultdict(lambda: dict.fromkeys(ACTIVITY_KEYS, 0))

    def add(timestamp, key, amount=1):
        day = timeutil.local_date_of(timestamp)
        if day is not None:
            buckets[day][key] += amount

    for (ts,) in db.query(SRSReviewLog.reviewed_at).filter(SRSReviewLog.user_id == user_id, SRSReviewLog.reviewed_at >= since):
        add(ts, "srs_reviews")
    for (ts,) in db.query(QuestionAttempt.created_at).filter(QuestionAttempt.user_id == user_id, QuestionAttempt.created_at >= since):
        add(ts, "questions_answered")
    for (ts,) in db.query(ErrorLog.created_at).filter(ErrorLog.user_id == user_id, ErrorLog.created_at >= since):
        add(ts, "errors_logged")
    for (ts,) in (
        db.query(SprintTask.completed_at)
        .join(Roadmap, Roadmap.id == SprintTask.roadmap_id)
        .filter(Roadmap.user_id == user_id, SprintTask.is_completed.is_(True), SprintTask.completed_at >= since)
    ):
        add(ts, "tasks_completed")
    for (ts,) in db.query(AIMessage.created_at).filter(
        AIMessage.user_id == user_id, AIMessage.role == "user", AIMessage.created_at >= since
    ):
        add(ts, "mentor_questions")
    return buckets


def _active_days(activity_counts: dict, minutes: dict) -> set:
    days = {day for day, counts in activity_counts.items() if sum(counts.values()) > 0}
    return days | {day for day, seconds in minutes.items() if seconds >= 60}


def streak_from(activity_counts: dict, today: date, minutes: Optional[dict] = None, study_days=None) -> int:
    """Consecutive active days. Planned rest days (not in `study_days`, Mon=0) neither count nor break it."""
    active = _active_days(activity_counts, minutes or {})
    rest = set(range(7)) - set(study_days) if study_days else set()
    day = today if today in active else today - timedelta(days=1)  # today not studied yet keeps the streak
    streak = 0
    while day in active or (day.weekday() in rest and day > today - timedelta(days=366)):
        streak += day in active
        day -= timedelta(days=1)
    return streak


def week_from(activity_counts: dict, today: date, minutes: Optional[dict] = None) -> list:
    minutes = minutes or {}
    monday = today - timedelta(days=today.weekday())
    days = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        counts = activity_counts.get(day) or dict.fromkeys(ACTIVITY_KEYS, 0)
        total = sum(counts.values())
        studied = round(minutes.get(day, 0) / 60)
        days.append(
            {
                "date": day,
                "weekday": WEEKDAY_LABELS[offset],
                "is_today": day == today,
                "is_future": day > today,
                **counts,
                "minutes": studied,
                "total": total,
                "active": total > 0 or studied >= 1,
            }
        )
    return days


# --------------------------------------------------------------------------- lessons, gaps
def lesson_titles(db: Session) -> dict:
    return {number: title for number, title in db.query(KnowledgeLesson.lesson_number, KnowledgeLesson.title)}


def _open_error_filter():
    return or_(ErrorLog.status.is_(None), ErrorLog.status != "mastered")


def severity_for(count: int) -> str:
    return "critical" if count >= 3 else "high" if count == 2 else "medium"


def recommendation_for(topic: str, count: int, lesson_number: Optional[int], titles: dict, traps: list = ()) -> str:
    examples = f" (bẫy: {', '.join(traps[:3])})" if traps else ""
    if lesson_number and lesson_number in titles:
        return f"Ôn {titles[lesson_number]} rồi làm lại {count} câu sai{examples}."
    return f"Làm lại {count} câu sai nhóm '{topic}'{examples}, ghi chú paraphrase và nghe/đọc lại đoạn gốc."


def gap_topic(log: ErrorLog, titles: dict) -> str:
    """Mistakes add up per syntax lesson (trap tags are almost unique per question), else per part + RCA code."""
    if log.lesson_number:
        return titles.get(log.lesson_number) or f"Bài {log.lesson_number:02d}"
    return f"{log.part or 'Khác'} · {log.error_type or 'TRAP'}"


def recompute_learning_gaps(db: Session, user_id: int) -> None:
    """Gaps are derived data: one row per lesson (or part + RCA code) that still has open errors."""
    open_logs = db.query(ErrorLog).filter(ErrorLog.user_id == user_id, _open_error_filter()).all()
    titles = lesson_titles(db)
    grouped = defaultdict(list)
    for log in open_logs:
        grouped[gap_topic(log, titles)].append(log)
    existing = {gap.topic: gap for gap in db.query(AILearningGap).filter_by(user_id=user_id).all()}
    now = timeutil.utcnow()
    for topic, logs in grouped.items():
        count = len(logs)
        lessons = Counter(log.lesson_number for log in logs if log.lesson_number)
        lesson = lessons.most_common(1)[0][0] if lessons else None
        traps = list(dict.fromkeys(log.topic for log in logs if log.topic))
        gap = existing.get(topic)
        if gap is None:
            gap = AILearningGap(user_id=user_id, topic=topic)
            db.add(gap)
        gap.error_count = count
        gap.severity = severity_for(count)
        gap.lesson_number = lesson
        gap.ai_recommendation = recommendation_for(topic, count, lesson, titles, traps)
        gap.is_resolved = False
        gap.updated_at = now
    for topic, gap in existing.items():
        if topic not in grouped and not gap.is_resolved:
            gap.is_resolved = True
            gap.updated_at = now
    db.commit()


def open_gaps(db: Session, user_id: int, limit: int = 5) -> list:
    titles = lesson_titles(db)
    gaps = (
        db.query(AILearningGap)
        .filter(AILearningGap.user_id == user_id, AILearningGap.is_resolved.is_(False))
        .order_by(AILearningGap.error_count.desc(), AILearningGap.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": gap.id,
            "topic": gap.topic,
            "error_count": gap.error_count or 0,
            "severity": gap.severity or "medium",
            "lesson_number": gap.lesson_number,
            "lesson_title": titles.get(gap.lesson_number),
            "ai_recommendation": gap.ai_recommendation,
        }
        for gap in gaps
    ]


def question_classes(db: Session) -> dict:
    return {q.id: {**curriculum.classify_question(q), "part": q.part} for q in db.query(TestQuestion).all()}


def latest_answers(db: Session, user_id: int) -> dict:
    """question_id -> is_correct of the learner's most recent attempt."""
    result = {}
    for question_id, is_correct in (
        db.query(QuestionAttempt.question_id, QuestionAttempt.is_correct)
        .filter(QuestionAttempt.user_id == user_id)
        .order_by(QuestionAttempt.created_at.asc(), QuestionAttempt.id.asc())
    ):
        result[question_id] = bool(is_correct)
    return result


def lesson_stats(db: Session, user_id: int, report=None) -> dict:
    from server.services import skills  # local import: skills is built on top of this module

    report = report or skills.compute(db, user_id)
    return {number: stat.lesson_stats() for number, stat in report.lessons.items()}


def recommended_lesson(db: Session, user_id: int, roadmap=None, report=None) -> Optional[dict]:
    """The planner's top focus lesson (same choice as today's plan)."""
    from server.services import planner, skills

    report = report or skills.compute(db, user_id)
    focus = planner.focus_lessons(db, user_id, report, roadmap if roadmap is not None else get_roadmap(db, user_id), limit=1)
    if not focus:
        return None
    pick = focus[0]
    lesson = db.query(KnowledgeLesson).filter_by(lesson_number=pick.lesson_number).first()
    stat = report.lessons[pick.lesson_number]
    return {
        "lesson_number": pick.lesson_number,
        "title": pick.title,
        "subtitle": lesson.subtitle if lesson else None,
        "syntax_formula": lesson.syntax_formula if lesson else None,
        "summary": lesson.summary if lesson else None,
        "reason": pick.reason,
        "question_count": stat.question_count,
        "accuracy": stat.accuracy,
        "mastery": round(stat.mastery, 4),
        "status": stat.status,
    }


# --------------------------------------------------------------------------- dashboard
def milestone_task(roadmap, gaps: Optional[dict] = None) -> Optional[dict]:
    """The next pending milestone the learner can actually work on (content exists in the bank)."""
    if roadmap is None:
        return None
    week = current_week(roadmap)
    gaps = gaps or {}
    open_tasks = [t for t in roadmap.tasks if not t.is_completed and t.id not in gaps]
    pending = next((t for t in open_tasks if t.week_number <= week), None) or next(iter(open_tasks), None)
    if pending is None:
        return None
    return {
        "key": f"roadmap-{pending.id}",
        "kind": "milestone",
        "tag": pending.category,
        "href": "/roadmaps",
        "done": False,
        "status": "pending",
        "auto": False,
        "title": pending.title,
        "detail": f"Mốc lộ trình tuần {pending.week_number}",
        "reason": None,
        "estimated_minutes": 0,
        "progress": None,
        "target": None,
        "plan_item_id": None,
        "lesson_number": None,
    }


def build_dashboard(db: Session, user_id: int) -> dict:
    from server.services import planner, skills

    user = get_or_create_user(db, user_id)
    ensure_srs_records(db, user_id)
    roadmap = get_roadmap(db, user_id)
    report = skills.compute(db, user_id)
    planner.ensure_plan(db, user_id, report=report)
    srs = srs_counts(db, user_id)
    today = timeutil.local_today()
    year_ago = today - timedelta(days=366)
    activity_counts = activity_by_date(db, user_id, year_ago)
    seconds = activity.seconds_by_day(db, user_id, year_ago)

    errors = db.query(ErrorLog).filter_by(user_id=user_id).all()
    rca = {code: 0 for code in curriculum.ERROR_TYPES}
    for error in errors:
        code = (error.error_type or "TRAP").upper()
        rca[code] = rca.get(code, 0) + 1
    open_errors = sum(1 for error in errors if (error.status or "unresolved") != "mastered")
    due_reviews = len(
        [e for e in errors if e.question_id and (e.status or "unresolved") != "mastered"
         and (e.next_review_at is None or timeutil.local_date_of(e.next_review_at) <= today)]
    )

    gaps = open_gaps(db, user_id)
    latest = (
        db.query(UserTestSubmission)
        .filter_by(user_id=user_id)
        .order_by(UserTestSubmission.submitted_at.desc(), UserTestSubmission.id.desc())
        .first()
    )
    week = current_week(roadmap) if roadmap else 1
    total_weeks = (roadmap.total_weeks or 24) if roadmap else 24
    done, total, percent = roadmap_progress(roadmap) if roadmap else (0, 0, 0)
    target = user.target_score or 800
    _, target_label, _ = scoring.cefr_for(target)

    plan_today = planner.items_for_day(db, user_id, today)
    tasks = [planner.as_task(item) for item in plan_today if item["status"] != "skipped"]
    milestone = milestone_task(roadmap, content_gaps(db, roadmap.tasks) if roadmap else None)
    if milestone:
        tasks.append(milestone)
    prediction = skills.predict_score(report, user)
    week_seconds = sum(seconds.get(today - timedelta(days=d), 0) for d in range(today.weekday() + 1))
    settings = planner.learner_settings(user)

    return {
        # Fields kept for the legacy UI (docs/index.html)
        "target_score": target,
        "roadmap_percent": percent,
        "completed_tasks": done,
        "total_tasks": total,
        "srs_due_count": srs["session_size"],
        "srs_mastered_count": srs["mastered"],
        "total_flashcards": db.query(Flashcard).count(),
        "total_errors": len(errors),
        "rca_breakdown": rca,
        "top_learning_gaps": [gap["topic"] for gap in gaps[:3]],
        # Connected fields
        "display_name": display_name(user),
        "headline": user.headline,
        "target_cefr": target_label,
        "daily_goal_minutes": user.daily_goal_minutes or 60,
        "current_week": week,
        "total_weeks": total_weeks,
        "current_phase": phase_of_week(learner_phases(roadmap), week) if roadmap else phase_for_week(week, total_weeks),
        "roadmap_title": roadmap.title if roadmap else None,
        "srs_review_due": srs["review_due"],
        "srs_new_available": srs["new_available"],
        "srs_reviewed_today": srs["reviewed_today"],
        "srs_learning_count": srs["learning"],
        "srs_new_cards_per_day": srs["new_cards_per_day"],
        "open_errors": open_errors,
        "error_reviews_due": due_reviews,
        "learning_gaps": gaps,
        "streak_days": streak_from(activity_counts, today, seconds, planner.parse_study_days(user.study_days)),
        "activity_week": week_from(activity_counts, today, seconds),
        "study_minutes_today": round(seconds.get(today, 0) / 60),
        "study_minutes_week": round(week_seconds / 60),
        "today_tasks": tasks,
        "today_plan_minutes": sum(t["estimated_minutes"] or 0 for t in tasks),
        "recommended_lesson": recommended_lesson(db, user_id, roadmap, report),
        "latest_submission": latest,
        "predicted_score": {
            "total": prediction["total"]["expected"],
            "low": prediction["total"]["low"],
            "high": prediction["total"]["high"],
            "listening": prediction["listening"]["expected"],
            "reading": prediction["reading"]["expected"],
            "confidence": prediction["confidence"],
            "confidence_level": prediction.get("confidence_level", "low"),
            "questions_needed_to_narrow": prediction.get("questions_needed_to_narrow", 0),
            "coverage": prediction.get("coverage"),
            "basis_listening": prediction["listening"]["basis"],
            "basis_reading": prediction["reading"]["basis"],
        },
        "onboarded": user.onboarded_at is not None,
        "exam_date": user.exam_date,
        "days_to_exam": planner.days_to_exam(settings),
        "exam_passed": settings.exam_passed is not None,
        "total_attempts": report.total_attempts,
    }


def learner_snapshot(db: Session, user_id: int) -> tuple:
    """(text for the LLM system prompt, dashboard dict) — kept for callers that want the short form."""
    from server.services import learner_context

    return learner_context.build(db, user_id)
