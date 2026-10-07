"""Agent tools: what the AI mentor (and one-click coach actions) can read and change.

Read tools return data for the model to reason with. Write tools change learner data and are
audited in AIActionLog together with the operations needed to undo them, so every change made by
the AI is visible and reversible from the UI (POST /api/ai/actions/{id}/undo).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from server.models import (
    AIActionLog,
    ErrorLog,
    Flashcard,
    KnowledgeLesson,
    LearnerMemory,
    LessonNote,
    ParaphrasePair,
    QuestionAttempt,
    Roadmap,
    SprintTask,
    SRSReviewLog,
    StudyPlanItem,
    StudyReminder,
    TestQuestion,
    User,
    UserCardSRS,
)
from server.services import curriculum, error_log_service, insights, planner, profile_service, vocab_service
from server.services import skills as skills_service
from server.utils import timeutil

logger = logging.getLogger(__name__)

MEMORY_CATEGORIES = ("goal", "preference", "struggle", "strength", "context", "other")
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ToolError(Exception):
    """Invalid input or state. The message is returned to the model / shown to the learner."""


@dataclass
class ToolContext:
    db: Session
    user_id: int
    source: str = "ai_mentor"  # ai_mentor | user | coach
    question: Optional[TestQuestion] = None


@dataclass
class Outcome:
    message: str
    data: dict = field(default_factory=dict)
    undo: list = field(default_factory=list)
    status: str = "success"  # success | exists | noop


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Callable
    writes: bool
    category: str


REGISTRY: dict = {}


def _tool(name: str, description: str, properties: Optional[dict] = None, required=(), *, writes: bool = False, category: str = "general"):
    def register(fn):
        schema = {"type": "object", "properties": properties or {}}
        if required:
            schema["required"] = list(required)
        REGISTRY[name] = ToolSpec(name, description, schema, fn, writes, category)
        return fn

    return register


def S(description: str, enum=None) -> dict:
    schema = {"type": "string", "description": description}
    if enum:
        schema["enum"] = list(enum)
    return schema


def I(description: str) -> dict:  # noqa: E743 - schema helper
    return {"type": "integer", "description": description}


def B(description: str) -> dict:
    return {"type": "boolean", "description": description}


def A(description: str, items: dict) -> dict:
    return {"type": "array", "description": description, "items": items}


def declarations() -> list:
    """Function declarations for the LLM (no-arg tools omit `parameters`, which Gemini requires)."""
    result = []
    for spec in REGISTRY.values():
        decl = {"name": spec.name, "description": spec.description}
        if spec.parameters.get("properties"):
            decl["parameters"] = spec.parameters
        result.append(decl)
    return result


def catalog() -> list:
    return [{"name": s.name, "description": s.description, "writes": s.writes, "category": s.category} for s in REGISTRY.values()]


# --------------------------------------------------------------------------- undo machinery
UNDO_MODELS = {
    cls.__name__: cls
    for cls in (User, Flashcard, UserCardSRS, SRSReviewLog, ErrorLog, StudyPlanItem, StudyReminder, LearnerMemory,
                LessonNote, ParaphrasePair, TestQuestion, SprintTask, Roadmap)
}


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def snapshot(obj, fields=None) -> dict:
    return {c.key: _jsonable(getattr(obj, c.key)) for c in obj.__table__.columns if fields is None or c.key in fields}


def _coerce(model, key: str, value):
    if value is None:
        return None
    try:
        python_type = model.__table__.columns[key].type.python_type
    except (KeyError, NotImplementedError):
        return value
    if python_type is datetime:
        return datetime.fromisoformat(value)
    if python_type is date:
        return date.fromisoformat(value)
    return value


def op_delete(obj) -> dict:
    return {"op": "delete", "model": type(obj).__name__, "id": obj.id}


def op_update(obj, fields) -> dict:
    return {"op": "update", "model": type(obj).__name__, "id": obj.id, "fields": snapshot(obj, set(fields))}


def op_insert(obj) -> dict:
    return {"op": "insert", "model": type(obj).__name__, "data": snapshot(obj)}


def op_call(name: str) -> dict:
    return {"op": "call", "name": name}  # recompute_gaps | replan | rescale


def _owner_ok(obj, user_id: int) -> bool:
    if isinstance(obj, User):
        return obj.id == user_id
    if isinstance(obj, SprintTask):
        return obj.roadmap is not None and obj.roadmap.user_id == user_id
    owner = getattr(obj, "user_id", None)
    return owner in (None, user_id)


def apply_undo(db: Session, user_id: int, ops: list) -> None:
    calls = []
    for op in ops:
        kind = op.get("op")
        if kind == "call":
            calls.append(op["name"])
            continue
        model = UNDO_MODELS[op["model"]]
        if kind == "delete":
            obj = db.get(model, op["id"])
            if obj is not None:
                if not _owner_ok(obj, user_id):
                    raise ToolError("Không có quyền hoàn tác bản ghi này")
                db.delete(obj)
        elif kind == "update":
            obj = db.get(model, op["id"])
            if obj is None:
                raise ToolError("Bản ghi đã bị xoá nên không thể hoàn tác")
            if not _owner_ok(obj, user_id):
                raise ToolError("Không có quyền hoàn tác bản ghi này")
            for key, value in op["fields"].items():
                setattr(obj, key, _coerce(model, key, value))
        elif kind == "insert":
            data = {key: _coerce(model, key, value) for key, value in op["data"].items()}
            if data.get("id") is not None and db.get(model, data["id"]) is not None:
                continue
            db.add(model(**data))
        db.flush()
    db.commit()
    user = db.get(User, user_id)
    if "rescale" in calls and user is not None:
        planner.rescale_roadmap(db, user)
        db.commit()
    if "recompute_gaps" in calls:
        insights.recompute_learning_gaps(db, user_id)
    if "replan" in calls:
        planner.ensure_plan(db, user_id, force=True)


def undo_action(db: Session, user_id: int, action_id: int) -> dict:
    action = db.query(AIActionLog).filter_by(id=action_id, user_id=user_id).first()
    if action is None:
        raise ToolError("Không tìm thấy thao tác")
    if action.status != "applied":
        raise ToolError("Thao tác này đã được hoàn tác")
    if not action.undo_json:
        raise ToolError("Thao tác này không hỗ trợ hoàn tác")
    apply_undo(db, user_id, json.loads(action.undo_json))
    action.status = "undone"
    action.undone_at = timeutil.utcnow()
    db.commit()
    return {"action_id": action.id, "status": "undone", "message": f"Đã hoàn tác: {action.summary}"}


def execute(ctx: ToolContext, name: str, args) -> dict:
    """Run one tool. Write tools are audited (with undo data) in the same transaction as their effect."""
    spec = REGISTRY.get(name)
    if spec is None:
        return {"tool": name, "status": "ignored", "message": f"Công cụ không tồn tại: {name}"}
    args = args if isinstance(args, dict) else {}
    try:
        outcome = spec.handler(ctx, args)
    except (ToolError, profile_service.ProfileError, ValueError) as exc:
        ctx.db.rollback()
        return {"tool": name, "status": "error", "message": str(exc), "writes": spec.writes}
    except Exception:
        ctx.db.rollback()
        logger.exception("Agent tool %s failed", name)
        return {"tool": name, "status": "error", "message": "Không thực hiện được thao tác, vui lòng thử lại.", "writes": spec.writes}
    result = {"tool": name, "status": outcome.status, "message": outcome.message, "writes": spec.writes}
    if outcome.data:
        # Results go back to the LLM as JSON: dates/datetimes must become strings.
        result["data"] = json.loads(json.dumps(outcome.data, ensure_ascii=False, default=str))
    if spec.writes and outcome.status == "success":
        action = AIActionLog(
            user_id=ctx.user_id,
            tool=name,
            source=ctx.source,
            summary=outcome.message,
            args_json=json.dumps(args, ensure_ascii=False, default=str)[:20000],
            result_json=json.dumps(outcome.data, ensure_ascii=False, default=str)[:20000] if outcome.data else None,
            undo_json=json.dumps(outcome.undo, ensure_ascii=False) if outcome.undo else None,
            status="applied",
        )
        ctx.db.add(action)
        ctx.db.commit()
        result["action_id"] = action.id
        result["undoable"] = bool(outcome.undo)
    else:
        ctx.db.commit()
    return result


# --------------------------------------------------------------------------- argument helpers
def _text(args: dict, key: str, *, required: bool = False, max_len: int = 2000) -> Optional[str]:
    value = args.get(key)
    text = str(value).strip() if value is not None else ""
    if required and not text:
        raise ToolError(f"Thiếu tham số '{key}'")
    return text[:max_len] or None


def _int(args: dict, key: str, *, low: Optional[int] = None, high: Optional[int] = None, required: bool = False) -> Optional[int]:
    value = args.get(key)
    if value in (None, ""):
        if required:
            raise ToolError(f"Thiếu tham số '{key}'")
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ToolError(f"'{key}' phải là số nguyên")
    if (low is not None and number < low) or (high is not None and number > high):
        raise ToolError(f"'{key}' phải trong khoảng {low}..{high}")
    return number


def _date(args: dict, key: str) -> Optional[date]:
    value = args.get(key)
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    today = timeutil.local_today()
    if text in ("today", "hôm nay", "hom nay"):
        return today
    if text in ("tomorrow", "ngày mai", "ngay mai"):
        return today + timedelta(days=1)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        raise ToolError(f"'{key}' phải có dạng YYYY-MM-DD")


def _lesson(args: dict, key: str = "lesson_number", required: bool = False) -> Optional[int]:
    return _int(args, key, low=1, high=12, required=required)


def _card(ctx: ToolContext, args: dict) -> Flashcard:
    card_id = _int(args, "card_id")
    if card_id:
        card = ctx.db.get(Flashcard, card_id)
    else:
        word = _text(args, "word", required=True, max_len=100)
        card = vocab_service.find_card(ctx.db, word)
    if card is None:
        raise ToolError("Không tìm thấy thẻ từ vựng này trong Sổ tay")
    return card


def _pct(value) -> Optional[int]:
    return None if value is None else round(value * 100)


# --------------------------------------------------------------------------- read tools
@_tool("get_learner_overview", "Đọc tổng quan cá nhân hoá mới nhất: hồ sơ & ngày thi, điểm dự đoán, kế hoạch hôm nay, SRS, sổ lỗi, chuỗi ngày học.", category="read")
def _get_overview(ctx: ToolContext, args: dict) -> Outcome:
    dash = insights.build_dashboard(ctx.db, ctx.user_id)
    user = profile_service.get_user(ctx.db, ctx.user_id)
    data = {
        "profile": profile_service.serialize(user),
        "predicted_score": dash["predicted_score"],
        "today_plan": [{"title": t["title"], "status": t["status"], "minutes": t["estimated_minutes"]} for t in dash["today_tasks"]],
        "srs": {"due_today": dash["srs_due_count"], "review_due": dash["srs_review_due"], "mastered": dash["srs_mastered_count"],
                "total": dash["total_flashcards"], "new_cards_per_day": dash["srs_new_cards_per_day"]},
        "errors": {"open": dash["open_errors"], "due_reviews": dash["error_reviews_due"], "rca": dash["rca_breakdown"]},
        "learning_gaps": [{"topic": g["topic"], "errors": g["error_count"], "lesson": g["lesson_number"]} for g in dash["learning_gaps"]],
        "streak_days": dash["streak_days"],
        "study_minutes_today": dash["study_minutes_today"],
        "daily_goal_minutes": dash["daily_goal_minutes"],
        "current_week": dash["current_week"],
        "total_weeks": dash["total_weeks"],
    }
    return Outcome("Đã đọc tổng quan học viên", data)


@_tool("get_weekly_report", "Đọc báo cáo 7 ngày qua: phút học, độ chính xác so với tuần trước, chuyên đề tiến bộ/đi xuống, câu sai mới/đã nắm chắc, SRS, hoàn thành kế hoạch, trọng tâm tuần tới.", category="read")
def _get_weekly_report(ctx: ToolContext, args: dict) -> Outcome:
    from server.services import weekly_report  # lazy: weekly_report imports planner/skills

    report = weekly_report.build(ctx.db, ctx.user_id)
    return Outcome("Đã đọc báo cáo tuần", {key: value for key, value in report.items() if key != "mastery_changes"}
                   | {"mastery_changes": report["mastery_changes"][:6]})


@_tool("get_skill_report", "Đọc mức thành thạo (mastery) theo 12 chuyên đề và theo Part, xu hướng, tốc độ/câu, tỉ lệ nhớ SRS, thẻ hay quên.", category="read")
def _get_skill_report(ctx: ToolContext, args: dict) -> Outcome:
    report = skills_service.compute(ctx.db, ctx.user_id)
    lessons = [
        {"lesson": s.lesson_number, "title": s.label, "mastery_pct": _pct(s.mastery) if s.attempts else None, "attempts": s.attempts,
         "status": s.status, "open_errors": s.open_errors, "trend_pct": _pct(s.trend), "unseen_questions": s.unseen_questions,
         "avg_seconds": round(s.avg_time_seconds, 1) if s.avg_time_seconds else None}
        for s in sorted(report.lessons.values(), key=lambda s: (s.attempts == 0, s.mastery))
    ]
    parts = [
        {"part": s.part, "mastery_pct": _pct(s.mastery) if s.attempts else None, "attempts": s.attempts, "avg_seconds": round(s.avg_time_seconds, 1) if s.avg_time_seconds else None,
         "target_seconds": s.target_seconds}
        for s in report.parts.values() if s.attempts or s.question_count
    ]
    user = profile_service.get_user(ctx.db, ctx.user_id)
    data = {
        "note": "mastery_pct = null nghĩa là chưa có dữ liệu luyện cho kỹ năng đó (không phải 0%)",
        "lessons": lessons,
        "parts": parts,
        "prediction": skills_service.predict_score(report, user)["total"],
        "srs_retention": skills_service.srs_retention(ctx.db, ctx.user_id),
        "leech_cards": skills_service.leech_cards(ctx.db, ctx.user_id),
    }
    return Outcome("Đã đọc báo cáo kỹ năng", data)


@_tool("search_flashcards", "Tìm thẻ trong Sổ tay từ vựng theo từ/nghĩa/collocation, kèm trạng thái SRS và số lần quên.",
       {"query": S("Từ khoá; bỏ trống để lấy các thẻ mới thêm gần đây"), "limit": I("Tối đa 25")}, category="read")
def _search_flashcards(ctx: ToolContext, args: dict) -> Outcome:
    query = _text(args, "query", max_len=100)
    limit = _int(args, "limit", low=1, high=25) or 10
    q = ctx.db.query(Flashcard)
    if query:
        pattern = f"%{query}%"
        q = q.filter(or_(Flashcard.word.ilike(pattern), Flashcard.meaning.ilike(pattern), Flashcard.collocations.ilike(pattern)))
    cards = q.order_by(Flashcard.id.desc()).limit(limit).all()
    ids = [c.id for c in cards]
    srs = {r.card_id: r for r in ctx.db.query(UserCardSRS).filter(UserCardSRS.user_id == ctx.user_id, UserCardSRS.card_id.in_(ids))} if ids else {}
    lapses = dict(
        ctx.db.query(SRSReviewLog.card_id, func.count(SRSReviewLog.id))
        .filter(SRSReviewLog.user_id == ctx.user_id, SRSReviewLog.rating == 1, SRSReviewLog.card_id.in_(ids))
        .group_by(SRSReviewLog.card_id)
    ) if ids else {}
    data = {"cards": [
        {"card_id": c.id, "word": c.word, "meaning": c.meaning, "category": c.category, "collocations": c.collocations,
         "state": srs[c.id].state if c.id in srs else None, "interval_days": srs[c.id].interval_days if c.id in srs else None,
         "lapses": lapses.get(c.id, 0)}
        for c in cards
    ]}
    return Outcome(f"Tìm thấy {len(cards)} thẻ", data)


@_tool("list_error_logs", "Liệt kê câu sai trong Sổ lỗi (mặc định: chưa nắm chắc), lọc theo mã RCA / chuyên đề / đến hạn ôn.",
       {"status": S("open = chưa nắm chắc, due = đến hạn ôn, mastered, all", ["open", "due", "mastered", "all"]),
        "error_type": S("Mã RCA", list(curriculum.ERROR_TYPES)), "lesson_number": I("Chuyên đề 1-12"), "limit": I("Tối đa 30")},
       category="read")
def _list_error_logs(ctx: ToolContext, args: dict) -> Outcome:
    status = args.get("status") or "open"
    limit = _int(args, "limit", low=1, high=30) or 10
    if status == "due":
        logs = error_log_service.due_reviews(ctx.db, ctx.user_id, limit=limit)
    else:
        q = ctx.db.query(ErrorLog).filter(ErrorLog.user_id == ctx.user_id)
        if status == "open":
            q = q.filter(error_log_service.open_filter())
        elif status == "mastered":
            q = q.filter(ErrorLog.status == "mastered")
        if args.get("error_type"):
            q = q.filter(ErrorLog.error_type == str(args["error_type"]).upper())
        lesson = _lesson(args)
        if lesson:
            q = q.filter(ErrorLog.lesson_number == lesson)
        logs = q.order_by(ErrorLog.created_at.desc()).limit(limit).all()
    data = {"errors": [
        {"error_id": l.id, "part": l.part, "question_no": l.question_no, "question_id": l.question_id, "error_type": l.error_type,
         "topic": l.topic, "lesson": l.lesson_number, "user_choice": l.user_choice, "correct_choice": l.correct_choice,
         "question": (l.question_content or "")[:200], "root_cause": l.root_cause[:300], "status": l.status,
         "review_stage": l.review_stage, "next_review": timeutil.local_date_of(l.next_review_at).isoformat() if l.next_review_at else None}
        for l in logs
    ]}
    return Outcome(f"{len(logs)} câu trong Sổ lỗi", data)


@_tool("get_study_plan", "Đọc kế hoạch học 7 ngày tới (nhiệm vụ, phút dự kiến, trạng thái) và chuyên đề trọng tâm.", category="read")
def _get_study_plan(ctx: ToolContext, args: dict) -> Outcome:
    view = planner.week_view(ctx.db, ctx.user_id)
    data = {
        "settings": view["settings"],
        "focus": view["focus"],
        "history": view["history"],
        "days": [
            {"date": d["date"].isoformat(), "weekday": d["weekday"], "planned_minutes": d["planned_minutes"],
             "items": [{"item_id": i["id"], "title": i["title"], "kind": i["kind"], "status": i["status"],
                        "minutes": i["estimated_minutes"], "source": i["source"], "href": i["href"],
                        "progress": i["progress"], "target": i["target_count"]} for i in d["items"]]}
            for d in view["days"]
        ],
    }
    return Outcome("Đã đọc kế hoạch học", data)


@_tool("get_lesson", "Đọc một chuyên đề cú pháp: công thức, tóm tắt, ghi chú riêng của học viên, thống kê luyện tập.",
       {"lesson_number": I("1-12")}, ["lesson_number"], category="read")
def _get_lesson(ctx: ToolContext, args: dict) -> Outcome:
    number = _lesson(args, required=True)
    lesson = ctx.db.query(KnowledgeLesson).filter_by(lesson_number=number).first()
    if lesson is None:
        raise ToolError("Không tìm thấy bài học")
    stat = skills_service.compute(ctx.db, ctx.user_id).lessons[number]
    notes = ctx.db.query(LessonNote).filter_by(user_id=ctx.user_id, lesson_number=number).order_by(LessonNote.id.desc()).limit(10).all()
    data = {
        "lesson_number": number, "title": lesson.title, "formula": lesson.syntax_formula, "summary": lesson.summary,
        "content_excerpt": (lesson.content_md or "")[:1500], "stats": stat.lesson_stats(),
        "notes": [{"note_id": n.id, "content": n.content, "source": n.source} for n in notes],
    }
    return Outcome(f"Đã đọc {lesson.title}", data)


@_tool("find_questions", "Tìm câu hỏi trong ngân hàng đề theo chuyên đề/Part, kèm kết quả lần làm gần nhất của học viên.",
       {"lesson_number": I("Chuyên đề 1-12"), "part": S("Part 1..7"), "only_wrong": B("Chỉ câu học viên đang làm sai"), "limit": I("Tối đa 10")},
       category="read")
def _find_questions(ctx: ToolContext, args: dict) -> Outcome:
    lesson = _lesson(args)
    part = curriculum.normalize_part(args.get("part")) if args.get("part") else None
    limit = _int(args, "limit", low=1, high=10) or 5
    latest = insights.latest_answers(ctx.db, ctx.user_id)
    q = ctx.db.query(TestQuestion)
    if part:
        q = q.filter(TestQuestion.part == part)
    rows = []
    for question in q.order_by(TestQuestion.test_id, TestQuestion.question_no):
        cls = curriculum.classify_question(question)
        if lesson and cls["lesson_number"] != lesson:
            continue
        if args.get("only_wrong") and latest.get(question.id) is not False:
            continue
        rows.append({"question_id": question.id, "test_id": question.test_id, "question_no": question.question_no, "part": question.part,
                     "sentence": question.sentence, "correct_choice": question.correct_choice, "trap_tag": cls["trap_tag"],
                     "lesson": cls["lesson_number"], "last_result": None if question.id not in latest else ("đúng" if latest[question.id] else "sai")})
        if len(rows) >= limit:
            break
    return Outcome(f"Tìm thấy {len(rows)} câu", {"questions": rows})


# --------------------------------------------------------------------------- write tools: profile & memory
@_tool(
    "update_learner_profile",
    "Cập nhật hồ sơ cá nhân hoá (mục tiêu, ngày thi, phút/ngày, ngày học, số thẻ mới/ngày, phong cách giải thích, Part ưu tiên, điểm đầu vào). Tự co giãn lộ trình và lập lại kế hoạch.",
    {
        "target_score": I("10-990"), "exam_date": S("YYYY-MM-DD"), "daily_goal_minutes": I("10-600"),
        "study_days": A("Ngày học trong tuần", S("T2..T7, CN hoặc 0-6 (T2=0)")), "new_cards_per_day": I("0-100"),
        "explanation_style": S("Phong cách giải thích", list(profile_service.EXPLANATION_STYLES)),
        "focus_parts": A("Part ưu tiên", S("Part 1..Part 7")), "baseline_listening": I("Điểm Listening hiện tại 5-495"),
        "baseline_reading": I("Điểm Reading hiện tại 5-495"), "display_name": S("Tên hiển thị"), "learning_goal_note": S("Ghi chú mục tiêu học"),
    },
    writes=True, category="profile",
)
def _update_profile(ctx: ToolContext, args: dict) -> Outcome:
    user = profile_service.get_user(ctx.db, ctx.user_id)
    changes = profile_service.normalize({k: v for k, v in args.items() if v is not None})
    if not changes:
        raise ToolError("Không có trường hợp lệ nào để cập nhật")
    old = profile_service.apply(ctx.db, user, changes)
    if not old:
        return Outcome("Hồ sơ không thay đổi", status="noop")
    undo = [{"op": "update", "model": "User", "id": user.id, "fields": {k: _jsonable(v) for k, v in old.items()}}]
    if "exam_date" in old:
        undo.append(op_call("rescale"))
    if profile_service.PLAN_FIELDS & old.keys():
        undo.append(op_call("replan"))
    labels = ", ".join(sorted(old))
    return Outcome(f"Đã cập nhật hồ sơ: {labels}", {"changed": sorted(old), "profile": profile_service.serialize(user)}, undo)


@_tool("remember_learner_fact", "Ghi nhớ lâu dài một thông tin ổn định về học viên (mục tiêu, sở thích học, điểm yếu lặp lại, bối cảnh công việc) để cá nhân hoá các lần sau.",
       {"content": S("Nội dung ngắn gọn, ngôi thứ ba"), "category": S("Loại", MEMORY_CATEGORIES)}, ["content"], writes=True, category="memory")
def _remember(ctx: ToolContext, args: dict) -> Outcome:
    content = _text(args, "content", required=True, max_len=500)
    category = args.get("category") if args.get("category") in MEMORY_CATEGORIES else "other"
    existing = (
        ctx.db.query(LearnerMemory)
        .filter(LearnerMemory.user_id == ctx.user_id, func.lower(LearnerMemory.content) == content.lower())
        .first()
    )
    if existing is not None:
        return Outcome(f"Đã ghi nhớ từ trước (#{existing.id})", {"memory_id": existing.id}, status="exists")
    memory = LearnerMemory(user_id=ctx.user_id, category=category, content=content, source=ctx.source)
    ctx.db.add(memory)
    ctx.db.flush()
    return Outcome(f"Đã ghi nhớ: {content}", {"memory_id": memory.id}, [op_delete(memory)])


@_tool("forget_learner_fact", "Xoá một điều đã ghi nhớ về học viên (khi sai hoặc học viên yêu cầu).", {"memory_id": I("ID ghi nhớ")}, ["memory_id"],
       writes=True, category="memory")
def _forget(ctx: ToolContext, args: dict) -> Outcome:
    memory = ctx.db.query(LearnerMemory).filter_by(id=_int(args, "memory_id", required=True), user_id=ctx.user_id).first()
    if memory is None:
        raise ToolError("Không tìm thấy ghi nhớ")
    undo = [op_insert(memory)]
    ctx.db.delete(memory)
    return Outcome(f"Đã quên: {memory.content}", {"memory_id": memory.id}, undo)


# --------------------------------------------------------------------------- write tools: vocabulary & SRS
CARD_FIELDS = {
    "word": S("Từ vựng tiếng Anh"), "meaning": S("Nghĩa tiếng Việt ngắn gọn"), "example_sentence": S("Câu ví dụ chuẩn đề TOEIC"),
    "example_translation": S("Bản dịch tiếng Việt của câu ví dụ"),
    "category": S("Chủ đề"), "collocations": S("Collocation, ngăn cách bằng dấu phẩy"), "paraphrase_pair": S("Cặp đồng nghĩa"),
    "ipa": S("Phiên âm IPA"), "word_type": S("verb / noun / adjective / adverb"),
}


@_tool("create_flashcard", "Thêm một từ vựng vào bộ thẻ SRS của học viên (bỏ qua nếu đã có).", CARD_FIELDS,
       ["word", "meaning", "example_sentence"], writes=True, category="vocab")
def _create_flashcard(ctx: ToolContext, args: dict) -> Outcome:
    try:
        card, created = vocab_service.create_card(ctx.db, ctx.user_id, args)
    except ValueError as exc:
        raise ToolError(str(exc))
    data = {"card_id": card.id, "word": card.word, "ipa": card.ipa, "meaning": card.meaning}
    if not created:
        return Outcome(f"Từ '{card.word}' đã có trong Sổ tay (#{card.id})", data, status="exists")
    return Outcome(f"Đã thêm '{card.word}' vào bộ thẻ SRS (#{card.id})", data, [op_delete(card)])


def _require_admin(ctx: ToolContext, action: str) -> None:
    """Flashcards are shared by every learner: only admins may change or remove them."""
    user = ctx.db.get(User, ctx.user_id)
    if user is None or user.role != "admin":
        raise ToolError(f"Chỉ quản trị viên mới được {action}; bạn có thể dời lịch ôn thẻ bằng reschedule_flashcard.")


@_tool("update_flashcard", "Sửa nội dung một thẻ dùng chung (chỉ quản trị viên).",
       {"card_id": I("ID thẻ"), **CARD_FIELDS}, writes=True, category="vocab")
def _update_flashcard(ctx: ToolContext, args: dict) -> Outcome:
    _require_admin(ctx, "sửa thẻ dùng chung")
    card = _card(ctx, {k: v for k, v in args.items() if k in ("card_id", "word")})
    fields = {}
    for key in ("meaning", "example_sentence", "example_translation", "category", "collocations", "paraphrase_pair", "word_type"):
        if args.get(key) not in (None, ""):
            fields[key] = str(args[key]).strip()
    if args.get("ipa"):
        fields["ipa"] = vocab_service.normalize_ipa(args["ipa"])
    if not fields:
        raise ToolError("Không có trường nào để sửa")
    undo = [op_update(card, fields)]
    for key, value in fields.items():
        setattr(card, key, value)
    return Outcome(f"Đã sửa thẻ '{card.word}': {', '.join(fields)}", {"card_id": card.id}, undo)


@_tool("delete_flashcard", "Xoá một thẻ dùng chung kèm lịch sử ôn (chỉ quản trị viên).",
       {"card_id": I("ID thẻ"), "word": S("Hoặc từ vựng")}, writes=True, category="vocab")
def _delete_flashcard(ctx: ToolContext, args: dict) -> Outcome:
    _require_admin(ctx, "xoá thẻ dùng chung")
    card = _card(ctx, args)
    srs_rows = ctx.db.query(UserCardSRS).filter_by(card_id=card.id).all()
    logs = ctx.db.query(SRSReviewLog).filter_by(card_id=card.id).all()
    undo = [op_insert(card)] + [op_insert(r) for r in srs_rows] + [op_insert(l) for l in logs]
    word = card.word
    for log in logs:
        ctx.db.delete(log)
    for row in srs_rows:
        ctx.db.delete(row)
    ctx.db.flush()
    ctx.db.delete(card)
    return Outcome(f"Đã xoá thẻ '{word}'", {"card_id": card.id}, undo)


@_tool("reschedule_flashcard", "Can thiệp lịch SRS của một thẻ: reset (học lại từ đầu), due_now (ôn ngay hôm nay) hoặc postpone (lùi N ngày).",
       {"card_id": I("ID thẻ"), "word": S("Hoặc từ vựng"), "action": S("Hành động", ["reset", "due_now", "postpone"]), "days": I("Số ngày lùi (postpone), 1-60")},
       ["action"], writes=True, category="vocab")
def _reschedule_flashcard(ctx: ToolContext, args: dict) -> Outcome:
    card = _card(ctx, args)
    row = ctx.db.query(UserCardSRS).filter_by(user_id=ctx.user_id, card_id=card.id).first()
    if row is None:
        raise ToolError("Thẻ chưa có lịch SRS")
    action = args.get("action")
    now = timeutil.utcnow()
    undo = [op_update(row, ("repetition_count", "ease_factor", "interval_days", "state", "next_review_at"))]
    if action == "reset":
        row.repetition_count, row.interval_days, row.state, row.next_review_at = 0, 1, "new", now
        row.ease_factor = max(1.3, row.ease_factor or 2.5)
        message = f"Đã đặt lại thẻ '{card.word}' về thẻ mới"
    elif action == "due_now":
        row.next_review_at = now
        if row.state == "new":
            row.state = "learning"
        message = f"Thẻ '{card.word}' sẽ xuất hiện trong phiên ôn hôm nay"
    elif action == "postpone":
        days = _int(args, "days", low=1, high=60) or 3
        row.next_review_at = max(row.next_review_at or now, now) + timedelta(days=days)
        message = f"Đã lùi thẻ '{card.word}' {days} ngày"
    else:
        raise ToolError("action phải là reset | due_now | postpone")
    return Outcome(message, {"card_id": card.id, "state": row.state}, undo)


# --------------------------------------------------------------------------- write tools: error log
@_tool(
    "log_error_question",
    "Lưu MỘT câu học viên đã làm sai vào Sổ lỗi kèm nguyên nhân gốc (RCA). Câu thuộc ngân hàng đề sẽ tự lấy đáp án đúng và lịch ôn 1-3-7 ngày.",
    {"part": S("Part 1..7"), "question_no": I("Số câu nếu biết"), "error_type": S("Mã RCA", list(curriculum.ERROR_TYPES)),
     "user_choice": S("Đáp án học viên chọn (A-D)"), "correct_choice": S("Đáp án đúng (A-D)"),
     "root_cause": S("Nguyên nhân gốc, ngắn gọn"), "key_rule": S("Quy tắc / cặp paraphrase cần nhớ")},
    ["error_type", "root_cause"], writes=True, category="errors",
)
def _log_error(ctx: ToolContext, args: dict) -> Outcome:
    error_type = str(args.get("error_type") or "").upper()
    fields = {
        "part": curriculum.normalize_part(args.get("part")),
        "question_no": args.get("question_no") if isinstance(args.get("question_no"), int) else None,
        "error_type": error_type if error_type in curriculum.ERROR_TYPES else None,
        "user_choice": error_log_service.normalize_choice(args.get("user_choice")),
        "correct_choice": error_log_service.normalize_choice(args.get("correct_choice")),
        "root_cause": _text(args, "root_cause"),
        "key_rule_or_paraphrase": _text(args, "key_rule"),
        "source": "ai_mentor",
    }
    question = ctx.question
    if question is None and fields["question_no"]:
        candidates = ctx.db.query(TestQuestion).filter_by(question_no=fields["question_no"]).limit(2).all()
        if len(candidates) == 1:  # only trust an unambiguous question number
            question = candidates[0]
    error_log_service.enrich_from_question(fields, question)
    before = None
    if fields.get("question_id"):
        before = (
            ctx.db.query(ErrorLog).filter_by(user_id=ctx.user_id, question_id=fields["question_id"]).order_by(ErrorLog.id.desc()).first()
        )
    undo_before = op_update(before, [c.key for c in ErrorLog.__table__.columns if c.key != "id"]) if before is not None else None
    log, status = error_log_service.upsert_error_log(ctx.db, ctx.user_id, fields, dedupe=True)
    ctx.db.commit()
    insights.recompute_learning_gaps(ctx.db, ctx.user_id)
    label = f"câu {log.question_no}" if log.question_no else "câu hỏi"
    verb = {"created": "Đã lưu", "updated": "Đã cập nhật", "reopened": "Đã mở lại"}[status]
    undo = [undo_before if undo_before else op_delete(log), op_call("recompute_gaps")]
    return Outcome(f"{verb} {label} ({log.part}) vào Sổ lỗi [{log.error_type}] (#{log.id})", {"error_log_id": log.id, "result": status}, undo)


@_tool("update_error_log", "Sửa phân tích hoặc trạng thái một câu trong Sổ lỗi (mã RCA, nguyên nhân, quy tắc nhớ, unresolved/reviewed/mastered).",
       {"error_id": I("ID câu trong Sổ lỗi"), "error_type": S("Mã RCA", list(curriculum.ERROR_TYPES)), "root_cause": S("Nguyên nhân gốc"),
        "key_rule": S("Quy tắc nhớ"), "status": S("Trạng thái", ["unresolved", "reviewed", "mastered"])},
       ["error_id"], writes=True, category="errors")
def _update_error_log(ctx: ToolContext, args: dict) -> Outcome:
    log = ctx.db.query(ErrorLog).filter_by(id=_int(args, "error_id", required=True), user_id=ctx.user_id).first()
    if log is None:
        raise ToolError("Không tìm thấy câu trong Sổ lỗi")
    tracked = ("error_type", "root_cause", "key_rule_or_paraphrase", "status", "review_stage", "next_review_at", "review_count", "source")
    undo = [op_update(log, tracked), op_call("recompute_gaps")]
    changed = []
    if args.get("error_type"):
        code = str(args["error_type"]).upper()
        if code not in curriculum.ERROR_TYPES:
            raise ToolError("Mã RCA không hợp lệ")
        log.error_type = code
        changed.append("error_type")
    if args.get("root_cause"):
        log.root_cause = _text(args, "root_cause")
        changed.append("root_cause")
    if args.get("key_rule"):
        log.key_rule_or_paraphrase = _text(args, "key_rule")
        changed.append("key_rule")
    if args.get("status"):
        if args["status"] not in ("unresolved", "reviewed", "mastered"):
            raise ToolError("Trạng thái không hợp lệ")
        error_log_service.apply_status(log, args["status"])
        changed.append("status")
    if not changed:
        raise ToolError("Không có gì để cập nhật")
    ctx.db.commit()
    insights.recompute_learning_gaps(ctx.db, ctx.user_id)
    return Outcome(f"Đã cập nhật câu sai #{log.id}: {', '.join(changed)}", {"error_log_id": log.id}, undo)


# --------------------------------------------------------------------------- write tools: plan & roadmap
@_tool("add_plan_item", "Thêm một nhiệm vụ vào kế hoạch học của một ngày (tối đa 60 ngày tới).",
       {"title": S("Tên nhiệm vụ"), "plan_date": S("YYYY-MM-DD, mặc định hôm nay"), "estimated_minutes": I("1-240"),
        "lesson_number": I("Chuyên đề liên quan 1-12"), "detail": S("Mô tả ngắn")},
       ["title"], writes=True, category="plan")
def _add_plan_item(ctx: ToolContext, args: dict) -> Outcome:
    day = _date(args, "plan_date") or timeutil.local_today()
    today = timeutil.local_today()
    if not today <= day <= today + timedelta(days=60):
        raise ToolError("Ngày phải từ hôm nay đến 60 ngày tới")
    item = StudyPlanItem(
        user_id=ctx.user_id, plan_date=day, kind="custom", title=_text(args, "title", required=True, max_len=300),
        detail=_text(args, "detail", max_len=1000), estimated_minutes=_int(args, "estimated_minutes", low=1, high=240) or 15,
        lesson_number=_lesson(args), status="pending", source=ctx.source, sort_order=50,
        reason="Do AI Mentor thêm theo yêu cầu" if ctx.source == "ai_mentor" else None,
    )
    ctx.db.add(item)
    ctx.db.flush()
    return Outcome(f"Đã thêm '{item.title}' vào kế hoạch {day.strftime('%d/%m')}", {"item_id": item.id}, [op_delete(item)])


@_tool("update_plan_item", "Đánh dấu xong/bỏ qua/đưa về chưa làm, dời ngày hoặc đổi tên một nhiệm vụ trong kế hoạch.",
       {"item_id": I("ID nhiệm vụ"), "status": S("Trạng thái", ["pending", "done", "skipped"]), "plan_date": S("Ngày mới YYYY-MM-DD"),
        "title": S("Tên mới")}, ["item_id"], writes=True, category="plan")
def _update_plan_item(ctx: ToolContext, args: dict) -> Outcome:
    item = ctx.db.query(StudyPlanItem).filter_by(id=_int(args, "item_id", required=True), user_id=ctx.user_id).first()
    if item is None:
        raise ToolError("Không tìm thấy nhiệm vụ")
    undo = [op_update(item, ("status", "plan_date", "title", "completed_at", "source"))]
    changed = []
    if args.get("status"):
        if args["status"] not in ("pending", "done", "skipped"):
            raise ToolError("Trạng thái không hợp lệ")
        item.status = args["status"]
        item.completed_at = timeutil.utcnow() if item.status == "done" else None
        changed.append(f"trạng thái → {item.status}")
    new_day = _date(args, "plan_date")
    if new_day:
        item.plan_date = new_day
        item.source = item.source if item.source != "planner" else ctx.source  # moved items survive replanning
        changed.append(f"ngày → {new_day.strftime('%d/%m')}")
    if args.get("title"):
        item.title = _text(args, "title", max_len=300)
        changed.append("tên")
    if not changed:
        raise ToolError("Không có gì để cập nhật")
    return Outcome(f"Đã cập nhật nhiệm vụ '{item.title}': {', '.join(changed)}", {"item_id": item.id}, undo)


@_tool("replan_week", "Lập lại kế hoạch 7 ngày tới từ dữ liệu học mới nhất (giữ nhiệm vụ đã xong/bỏ qua và nhiệm vụ tự thêm).",
       {"reason": S("Lý do lập lại")}, writes=True, category="plan")
def _replan_week(ctx: ToolContext, args: dict) -> Outcome:
    today = timeutil.local_today()
    end = today + timedelta(days=planner.PLAN_DAYS)
    old = (
        ctx.db.query(StudyPlanItem)
        .filter(StudyPlanItem.user_id == ctx.user_id, StudyPlanItem.plan_date >= today, StudyPlanItem.plan_date < end,
                StudyPlanItem.source == "planner", StudyPlanItem.status == "pending")
        .all()
    )
    undo_restore = [op_insert(item) for item in old]
    created = planner.generate_plan(ctx.db, ctx.user_id, today)
    undo = [op_delete(item) for item in created] + undo_restore
    minutes = sum(item.estimated_minutes or 0 for item in created)
    return Outcome(f"Đã lập lại kế hoạch: {len(created)} nhiệm vụ (~{minutes} phút) cho 7 ngày tới",
                   {"items": len(created), "minutes": minutes}, undo)


@_tool("set_roadmap_task", "Đánh dấu hoàn thành / chưa hoàn thành một mốc trong lộ trình dài hạn.",
       {"task_id": I("ID mốc"), "is_completed": B("Đã hoàn thành?")}, ["task_id", "is_completed"], writes=True, category="plan")
def _set_roadmap_task(ctx: ToolContext, args: dict) -> Outcome:
    task = (
        ctx.db.query(SprintTask).join(Roadmap, Roadmap.id == SprintTask.roadmap_id)
        .filter(SprintTask.id == _int(args, "task_id", required=True), Roadmap.user_id == ctx.user_id).first()
    )
    if task is None:
        raise ToolError("Không tìm thấy mốc lộ trình")
    done = bool(args.get("is_completed"))
    undo = [op_update(task, ("is_completed", "completed_at"))]
    task.is_completed = done
    task.completed_at = timeutil.utcnow() if done else None
    return Outcome(f"{'Đã hoàn thành' if done else 'Đã mở lại'} mốc: {task.title}", {"task_id": task.id}, undo)


@_tool("update_roadmap", "Đổi ngày bắt đầu hoặc tên lộ trình dài hạn (mốc sẽ tự co giãn theo ngày thi).",
       {"start_date": S("YYYY-MM-DD"), "title": S("Tên lộ trình")}, writes=True, category="plan")
def _update_roadmap(ctx: ToolContext, args: dict) -> Outcome:
    roadmap = insights.get_roadmap(ctx.db, ctx.user_id)
    if roadmap is None:
        raise ToolError("Chưa có lộ trình")
    start = _date(args, "start_date")
    title = _text(args, "title", max_len=150)
    if not start and not title:
        raise ToolError("Không có gì để cập nhật")
    undo = [op_update(roadmap, ("start_date", "title")), op_call("rescale"), op_call("replan")]
    if start:
        roadmap.start_date = start
    if title:
        roadmap.title = title
    planner.rescale_roadmap(ctx.db, profile_service.get_user(ctx.db, ctx.user_id))
    ctx.db.commit()
    planner.ensure_plan(ctx.db, ctx.user_id, force=True)
    return Outcome("Đã cập nhật lộ trình", {"current_week": insights.current_week(roadmap), "total_weeks": roadmap.total_weeks}, undo)


# --------------------------------------------------------------------------- write tools: content
@_tool("add_lesson_note", "Thêm ghi chú cá nhân vào một chuyên đề (mẹo nhớ, quy tắc rút ra từ lỗi của học viên).",
       {"lesson_number": I("1-12"), "content": S("Nội dung ghi chú (Markdown)")}, ["lesson_number", "content"], writes=True, category="content")
def _add_lesson_note(ctx: ToolContext, args: dict) -> Outcome:
    note = LessonNote(user_id=ctx.user_id, lesson_number=_lesson(args, required=True), content=_text(args, "content", required=True, max_len=4000),
                      source=ctx.source)
    ctx.db.add(note)
    ctx.db.flush()
    return Outcome(f"Đã thêm ghi chú vào Bài {note.lesson_number:02d}", {"note_id": note.id, "lesson_number": note.lesson_number}, [op_delete(note)])


@_tool("add_paraphrase_pair", "Thêm một cặp paraphrase vào Paraphrase Vault (từ trong bài ↔ từ trong đáp án).",
       {"word_in_text": S("Cụm trong bài đọc/nghe"), "word_in_answer": S("Cụm tương đương trong đáp án"), "meaning": S("Nghĩa tiếng Việt"),
        "part_target": S("Part hay gặp")}, ["word_in_text", "word_in_answer"], writes=True, category="content")
def _add_paraphrase(ctx: ToolContext, args: dict) -> Outcome:
    text = _text(args, "word_in_text", required=True, max_len=100)
    answer = _text(args, "word_in_answer", required=True, max_len=100)
    existing = ctx.db.query(ParaphrasePair).filter(func.lower(ParaphrasePair.word_in_text) == text.lower(),
                                                   func.lower(ParaphrasePair.word_in_answer) == answer.lower()).first()
    if existing is not None:
        return Outcome(f"Cặp '{text} = {answer}' đã có", {"pair_id": existing.id}, status="exists")
    pair = ParaphrasePair(word_in_text=text, word_in_answer=answer, meaning=_text(args, "meaning", max_len=200),
                          part_target=_text(args, "part_target", max_len=20) or "Part 7")
    ctx.db.add(pair)
    ctx.db.flush()
    return Outcome(f"Đã thêm paraphrase: {text} = {answer}", {"pair_id": pair.id}, [op_delete(pair)])


# --------------------------------------------------------------------------- write tools: reminders
@_tool("schedule_study_reminder", "Đặt lịch nhắc học hằng ngày cho học viên.",
       {"scheduled_time": S("HH:MM (24h)"), "message": S("Nội dung nhắc"), "reminder_type": S("Loại (weekly_report = báo cáo tuần, gửi Chủ nhật)", ["daily_study", "review_error_log", "srs_due", "weekly_report"])},
       ["scheduled_time", "message"], writes=True, category="reminders")
def _schedule_reminder(ctx: ToolContext, args: dict) -> Outcome:
    scheduled = str(args.get("scheduled_time") or "").strip()
    if not HHMM_RE.match(scheduled):
        raise ToolError("Giờ nhắc phải có dạng HH:MM (24h)")
    kind = args.get("reminder_type") if args.get("reminder_type") in ("daily_study", "review_error_log", "srs_due", "weekly_report") else "daily_study"
    reminder = StudyReminder(user_id=ctx.user_id, reminder_type=kind, scheduled_time=scheduled,
                             message=_text(args, "message", max_len=500) or "Đến giờ ôn TOEIC rồi!", is_active=True)
    ctx.db.add(reminder)
    ctx.db.flush()
    return Outcome(f"Đã đặt lịch nhắc lúc {reminder.scheduled_time} (#{reminder.id})", {"reminder_id": reminder.id}, [op_delete(reminder)])


@_tool("update_reminder", "Sửa giờ / nội dung / bật-tắt một lịch nhắc.",
       {"reminder_id": I("ID lịch nhắc"), "scheduled_time": S("HH:MM"), "message": S("Nội dung"), "is_active": B("Bật?")},
       ["reminder_id"], writes=True, category="reminders")
def _update_reminder(ctx: ToolContext, args: dict) -> Outcome:
    reminder = ctx.db.query(StudyReminder).filter_by(id=_int(args, "reminder_id", required=True), user_id=ctx.user_id).first()
    if reminder is None:
        raise ToolError("Không tìm thấy lịch nhắc")
    undo = [op_update(reminder, ("scheduled_time", "message", "is_active"))]
    if args.get("scheduled_time"):
        if not HHMM_RE.match(str(args["scheduled_time"])):
            raise ToolError("Giờ nhắc phải có dạng HH:MM (24h)")
        reminder.scheduled_time = str(args["scheduled_time"])
    if args.get("message"):
        reminder.message = _text(args, "message", max_len=500)
    if args.get("is_active") is not None:
        reminder.is_active = bool(args["is_active"])
    return Outcome(f"Đã cập nhật lịch nhắc {reminder.scheduled_time}", {"reminder_id": reminder.id}, undo)


@_tool("delete_reminder", "Xoá một lịch nhắc.", {"reminder_id": I("ID lịch nhắc")}, ["reminder_id"], writes=True, category="reminders")
def _delete_reminder(ctx: ToolContext, args: dict) -> Outcome:
    reminder = ctx.db.query(StudyReminder).filter_by(id=_int(args, "reminder_id", required=True), user_id=ctx.user_id).first()
    if reminder is None:
        raise ToolError("Không tìm thấy lịch nhắc")
    undo = [op_insert(reminder)]
    ctx.db.delete(reminder)
    return Outcome(f"Đã xoá lịch nhắc {reminder.scheduled_time}", {"reminder_id": reminder.id}, undo)


def recent_actions(db: Session, user_id: int, limit: int = 50) -> list:
    rows = db.query(AIActionLog).filter_by(user_id=user_id).order_by(AIActionLog.id.desc()).limit(limit).all()
    return [
        {"id": r.id, "tool": r.tool, "source": r.source, "summary": r.summary, "status": r.status,
         "undoable": bool(r.undo_json) and r.status == "applied", "created_at": r.created_at, "undone_at": r.undone_at}
        for r in rows
    ]


def attempts_for_question(db: Session, user_id: int, question_id: int) -> int:
    return db.query(QuestionAttempt).filter_by(user_id=user_id, question_id=question_id).count()
