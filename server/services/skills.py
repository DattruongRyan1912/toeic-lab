"""Skill model built from the learner's own history.

* Mastery per syntax lesson (Bài 01-12), per TOEIC part and per section: a recency-weighted Beta posterior
  (half-life 14 days) with a prior taken from the onboarding baseline score, so a few answers move the estimate
  but never to 0% / 100%.
* Trend (last 7 days vs the 3 weeks before), pace (seconds per question vs a target) and coverage of the bank.
* Score prediction for the real test (L: Part 1-4, R: Part 5-7 weighted by their question counts) with a range
  that widens when there is little data, plus honest "basis" (data / baseline / prior).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from server.models import ErrorLog, KnowledgeLesson, QuestionAttempt, SRSReviewLog, TestQuestion, User, UserCardSRS, Flashcard
from server.services import curriculum, scoring
from server.utils import timeutil

HALF_LIFE_DAYS = 14.0
PRIOR_STRENGTH = 2.0
DEFAULT_PRIOR = 0.55
CONFIDENCE_K = 3.0
STRONG_MASTERY = 0.8
OK_MASTERY = 0.6

PART_SIZES = {"Part 1": 6, "Part 2": 25, "Part 3": 39, "Part 4": 30, "Part 5": 30, "Part 6": 16, "Part 7": 54}
SECTION_PARTS = {
    "listening": ("Part 1", "Part 2", "Part 3", "Part 4"),
    "reading": ("Part 5", "Part 6", "Part 7"),
}
# Comfortable pace in the real test (seconds per question)
TARGET_SECONDS = {"Part 1": 20, "Part 2": 20, "Part 3": 30, "Part 4": 30, "Part 5": 22, "Part 6": 30, "Part 7": 55}


@dataclass
class SkillStat:
    key: str
    label: str
    kind: str  # lesson | part | section
    lesson_number: Optional[int] = None
    part: Optional[str] = None
    attempts: int = 0
    distinct_questions: int = 0
    latest_correct: int = 0
    accuracy: Optional[float] = None  # share of distinct questions whose latest answer is correct
    mastery: float = DEFAULT_PRIOR
    prior: float = DEFAULT_PRIOR
    confidence: float = 0.0
    trend: Optional[float] = None
    avg_time_seconds: Optional[float] = None
    target_seconds: Optional[int] = None
    last_attempt_at: Optional[datetime] = None
    open_errors: int = 0
    question_count: int = 0
    unseen_questions: int = 0
    status: str = "not_started"  # not_started | weak | improving | strong

    def as_dict(self) -> dict:
        data = asdict(self)
        for key in ("mastery", "prior", "confidence", "accuracy", "trend"):
            if data[key] is not None:
                data[key] = round(data[key], 4)
        if data["avg_time_seconds"] is not None:
            data["avg_time_seconds"] = round(data["avg_time_seconds"], 1)
        return data

    def lesson_stats(self) -> dict:
        """Shape used by /api/knowledge/lessons (kept for compatibility, plus mastery fields)."""
        return {
            "question_count": self.question_count,
            "answered": self.distinct_questions,
            "correct": self.latest_correct,
            "accuracy": round(self.accuracy, 4) if self.accuracy is not None else None,
            "open_errors": self.open_errors,
            "status": self.status,
            "mastery": round(self.mastery, 4),
            "confidence": round(self.confidence, 4),
            "attempts": self.attempts,
            "avg_time_seconds": round(self.avg_time_seconds, 1) if self.avg_time_seconds is not None else None,
            "trend": round(self.trend, 4) if self.trend is not None else None,
        }


@dataclass
class SkillReport:
    lessons: dict = field(default_factory=dict)  # lesson_number -> SkillStat
    parts: dict = field(default_factory=dict)  # "Part 5" -> SkillStat
    sections: dict = field(default_factory=dict)  # "listening"/"reading" -> SkillStat
    priors: dict = field(default_factory=dict)
    total_attempts: int = 0
    generated_at: Optional[datetime] = None

    def weakest_lessons(self, limit: int = 3, min_attempts: int = 1) -> list:
        candidates = [s for s in self.lessons.values() if s.attempts >= min_attempts]
        return sorted(candidates, key=lambda s: (s.mastery, -s.open_errors, s.lesson_number))[:limit]

    def strongest_lessons(self, limit: int = 2) -> list:
        candidates = [s for s in self.lessons.values() if s.attempts >= 3]
        return sorted(candidates, key=lambda s: (-s.mastery, s.lesson_number))[:limit]


# --------------------------------------------------------------------------- priors
def inverse_scaled(section: str, scaled: int) -> int:
    """Smallest raw score (0-100) whose scaled score reaches `scaled`."""
    convert = scoring.listening_scaled if section == "listening" else scoring.reading_scaled
    for raw in range(0, 101):
        if convert(raw) >= scaled:
            return raw
    return 100


def section_priors(user: Optional[User]) -> dict:
    priors = {}
    for section, attr in (("listening", "baseline_listening"), ("reading", "baseline_reading")):
        baseline = getattr(user, attr, None) if user is not None else None
        if baseline:
            priors[section] = min(0.95, max(0.1, inverse_scaled(section, int(baseline)) / 100))
        else:
            priors[section] = DEFAULT_PRIOR
    return priors


def section_of(part: Optional[str]) -> str:
    return "listening" if part in SECTION_PARTS["listening"] else "reading"


# --------------------------------------------------------------------------- estimation
def _status(stat: SkillStat) -> str:
    if stat.attempts == 0:
        return "not_started"
    if stat.mastery >= STRONG_MASTERY and stat.distinct_questions >= 3:
        return "strong"
    if stat.mastery >= OK_MASTERY:
        return "improving"
    return "weak"


def estimate(stat: SkillStat, attempts: list, prior: float, now: datetime) -> SkillStat:
    stat.prior = prior
    stat.attempts = len(attempts)
    a0, b0 = prior * PRIOR_STRENGTH, (1 - prior) * PRIOR_STRENGTH
    weight_sum = weighted_correct = 0.0
    latest: dict = {}
    recent, older, times = [], [], []
    for attempt in attempts:
        age_days = max(0.0, (now - attempt.created_at).total_seconds() / 86400) if attempt.created_at else 0.0
        weight = 0.5 ** (age_days / HALF_LIFE_DAYS)
        weight_sum += weight
        weighted_correct += weight * (1.0 if attempt.is_correct else 0.0)
        latest[attempt.question_id] = bool(attempt.is_correct)
        if age_days <= 7:
            recent.append(attempt.is_correct)
        elif age_days <= 28:
            older.append(attempt.is_correct)
        if attempt.time_ms and attempt.choice:
            times.append(attempt.time_ms / 1000)
        if stat.last_attempt_at is None or (attempt.created_at and attempt.created_at > stat.last_attempt_at):
            stat.last_attempt_at = attempt.created_at
    stat.mastery = (a0 + weighted_correct) / (a0 + b0 + weight_sum)
    stat.confidence = weight_sum / (weight_sum + CONFIDENCE_K)
    stat.distinct_questions = len(latest)
    stat.latest_correct = sum(1 for ok in latest.values() if ok)
    stat.accuracy = stat.latest_correct / stat.distinct_questions if latest else None
    if len(recent) >= 3 and len(older) >= 3:
        stat.trend = sum(recent) / len(recent) - sum(older) / len(older)
    if times:
        last = times[-20:]
        stat.avg_time_seconds = sum(last) / len(last)
    stat.status = _status(stat)
    return stat


def compute(db: Session, user_id: int, now: Optional[datetime] = None) -> SkillReport:
    now = now or timeutil.utcnow()
    user = db.get(User, user_id)
    priors = section_priors(user)
    titles = {n: t for n, t in db.query(KnowledgeLesson.lesson_number, KnowledgeLesson.title)}

    report = SkillReport(priors=priors, generated_at=now)
    for number in range(1, 13):
        report.lessons[number] = SkillStat(
            key=f"lesson:{number}", label=titles.get(number, f"Bài {number:02d}"), kind="lesson",
            lesson_number=number, part="Part 5", target_seconds=TARGET_SECONDS["Part 5"],
        )
    for part in PART_SIZES:
        report.parts[part] = SkillStat(key=f"part:{part}", label=part, kind="part", part=part, target_seconds=TARGET_SECONDS[part])
    for section in SECTION_PARTS:
        report.sections[section] = SkillStat(key=f"section:{section}", label=section.capitalize(), kind="section")

    meta = {}
    bank_by_lesson, bank_by_part = defaultdict(set), defaultdict(set)
    for question in db.query(TestQuestion).all():
        cls = curriculum.classify_question(question)
        meta[question.id] = (cls["lesson_number"], question.part)
        if cls["lesson_number"]:
            bank_by_lesson[cls["lesson_number"]].add(question.id)
        if question.part in report.parts:
            bank_by_part[question.part].add(question.id)

    attempts = (
        db.query(QuestionAttempt)
        .filter(QuestionAttempt.user_id == user_id, QuestionAttempt.created_at <= now)  # `now` in the past = snapshot
        .order_by(QuestionAttempt.created_at.asc(), QuestionAttempt.id.asc())
        .all()
    )
    report.total_attempts = len(attempts)
    by_lesson, by_part, by_section = defaultdict(list), defaultdict(list), defaultdict(list)
    for attempt in attempts:
        lesson, part = meta.get(attempt.question_id, (None, None))
        lesson = lesson or attempt.lesson_number
        part = part or attempt.part
        if lesson in report.lessons:
            by_lesson[lesson].append(attempt)
        if part in report.parts:
            by_part[part].append(attempt)
            by_section[section_of(part)].append(attempt)

    open_by_lesson, open_by_part = Counter(), Counter()
    for lesson_number, part in (
        db.query(ErrorLog.lesson_number, ErrorLog.part)
        .filter(ErrorLog.user_id == user_id)
        .filter((ErrorLog.status.is_(None)) | (ErrorLog.status != "mastered"))
    ):
        if lesson_number:
            open_by_lesson[lesson_number] += 1
        if part:
            open_by_part[part] += 1

    for number, stat in report.lessons.items():
        estimate(stat, by_lesson.get(number, []), priors["reading"], now)
        stat.question_count = len(bank_by_lesson.get(number, ()))
        seen = {a.question_id for a in by_lesson.get(number, [])}
        stat.unseen_questions = len(bank_by_lesson.get(number, set()) - seen)
        stat.open_errors = open_by_lesson.get(number, 0)
    for part, stat in report.parts.items():
        estimate(stat, by_part.get(part, []), priors[section_of(part)], now)
        stat.question_count = len(bank_by_part.get(part, ()))
        seen = {a.question_id for a in by_part.get(part, [])}
        stat.unseen_questions = len(bank_by_part.get(part, set()) - seen)
        stat.open_errors = open_by_part.get(part, 0)
    for section, stat in report.sections.items():
        estimate(stat, by_section.get(section, []), priors[section], now)
    return report


# --------------------------------------------------------------------------- prediction
def predict_score(report: SkillReport, user: Optional[User] = None) -> dict:
    target = (getattr(user, "target_score", None) or 800) if user is not None else 800
    has_baseline = {
        "listening": bool(getattr(user, "baseline_listening", None)) if user is not None else False,
        "reading": bool(getattr(user, "baseline_reading", None)) if user is not None else False,
    }
    result: dict = {}
    total_conf = 0.0
    for section, parts in SECTION_PARTS.items():
        convert = scoring.listening_scaled if section == "listening" else scoring.reading_scaled
        prior = report.priors.get(section, DEFAULT_PRIOR)
        observed = [report.parts[p] for p in parts if report.parts[p].attempts]
        # Parts without data borrow from the observed parts of the same section, blended with the prior.
        fill = (sum(s.mastery * s.confidence for s in observed) + prior) / (sum(s.confidence for s in observed) + 1)
        raw = low = high = conf = 0.0
        breakdown = {}
        for part in parts:
            size, stat = PART_SIZES[part], report.parts[part]
            accuracy, confidence = (stat.mastery, stat.confidence) if stat.attempts else (fill, 0.0)
            spread = 0.08 + 0.22 * (1 - confidence)
            raw += size * accuracy
            low += size * max(0.0, accuracy - spread)
            high += size * min(1.0, accuracy + spread)
            conf += size * confidence
            breakdown[part] = {"accuracy": round(accuracy, 3), "confidence": round(confidence, 3), "observed": bool(stat.attempts)}
        basis = "data" if observed else ("baseline" if has_baseline[section] else "prior")
        result[section] = {
            "expected": convert(round(raw)),
            "low": convert(round(low)),
            "high": convert(round(high)),
            "expected_raw": round(raw),
            "basis": basis,
            "confidence": round(conf / 100, 3),
            "parts": breakdown,
        }
        total_conf += conf
    expected = result["listening"]["expected"] + result["reading"]["expected"]
    _, cefr_label, _ = scoring.cefr_for(expected)
    overall_conf = round(total_conf / 200, 3)
    conf_level = "high" if overall_conf >= 0.75 else ("medium" if overall_conf >= 0.40 else "low")
    if overall_conf >= 0.75:
        needed_questions = 0
    elif report.total_attempts < 40:
        needed_questions = 40 - report.total_attempts
    else:
        needed_questions = max(5, int((0.75 - overall_conf) * 50))
    result["total"] = {
        "expected": expected,
        "low": result["listening"]["low"] + result["reading"]["low"],
        "high": result["listening"]["high"] + result["reading"]["high"],
        "cefr": cefr_label,
    }
    result["confidence"] = overall_conf
    result["confidence_level"] = conf_level
    result["questions_needed_to_narrow"] = needed_questions
    result["target_score"] = target
    result["target_gap"] = max(0, target - expected)
    return result


# --------------------------------------------------------------------------- SRS quality
def srs_retention(db: Session, user_id: int, days: int = 30) -> dict:
    since = timeutil.utcnow() - timedelta(days=days)
    ratings = [
        rating
        for (rating,) in db.query(SRSReviewLog.rating).filter(
            SRSReviewLog.user_id == user_id,
            SRSReviewLog.reviewed_at >= since,
            SRSReviewLog.prev_state != "new",
        )
    ]
    retained = sum(1 for rating in ratings if rating >= 2)
    return {"reviews": len(ratings), "retained": retained, "rate": round(retained / len(ratings), 4) if ratings else None, "days": days}


def leech_cards(db: Session, user_id: int, min_lapses: int = 3, limit: int = 10) -> list:
    lapses = Counter(
        card_id
        for (card_id,) in db.query(SRSReviewLog.card_id).filter(SRSReviewLog.user_id == user_id, SRSReviewLog.rating == 1)
    )
    ids = [card_id for card_id, count in lapses.most_common() if count >= min_lapses][:limit]
    if not ids:
        return []
    cards = {card.id: card for card in db.query(Flashcard).filter(Flashcard.id.in_(ids))}
    states = {row.card_id: row.state for row in db.query(UserCardSRS).filter(UserCardSRS.user_id == user_id, UserCardSRS.card_id.in_(ids))}
    return [
        {"card_id": card_id, "word": cards[card_id].word, "meaning": cards[card_id].meaning, "lapses": lapses[card_id], "state": states.get(card_id)}
        for card_id in ids
        if card_id in cards
    ]


def pace_summary(report: SkillReport) -> list:
    rows = []
    for part, stat in report.parts.items():
        if stat.avg_time_seconds is None:
            continue
        rows.append(
            {
                "part": part,
                "avg_seconds": round(stat.avg_time_seconds, 1),
                "target_seconds": stat.target_seconds,
                "slow": bool(stat.target_seconds and stat.avg_time_seconds > stat.target_seconds * 1.3),
            }
        )
    return rows


def percent(value: Optional[float]) -> str:
    return "—" if value is None else f"{round(value * 100)}%"


def short_summary(report: SkillReport) -> str:
    weak = report.weakest_lessons(3)
    if not weak:
        return "Chưa có dữ liệu luyện tập"
    return "; ".join(f"{s.label} {percent(s.mastery)} ({s.attempts} câu, {s.open_errors} lỗi mở)" for s in weak)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ceil_div(a: float, b: float) -> int:
    return int(math.ceil(a / b)) if b else 0
