from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.models import KnowledgeLesson, LessonNote, LessonProgress, ParaphrasePair, TestQuestion
from server.schemas import (
    KnowledgeLessonDetail,
    KnowledgeLessonRead,
    LessonNoteCreate,
    LessonNoteRead,
    LessonProgressRead,
    LessonProgressUpdate,
    ParaphrasePairRead,
)
from server.services import activity, curriculum, insights
from server.routers.test_router import serialize_question
from server.utils import timeutil

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Vault"])

EMPTY_STATS = {"question_count": 0, "answered": 0, "correct": 0, "accuracy": None, "open_errors": 0, "status": "not_started"}


def _serialize_lesson(lesson: KnowledgeLesson, stats: dict) -> dict:
    return {
        "id": lesson.id,
        "lesson_number": lesson.lesson_number,
        "title": lesson.title,
        "subtitle": lesson.subtitle,
        "syntax_formula": lesson.syntax_formula,
        "summary": lesson.summary,
        "content_html": lesson.content_html,
        "is_unlocked": bool(lesson.is_unlocked),
        "has_full_content": bool(lesson.content_md),
        "stats": stats.get(lesson.lesson_number) or EMPTY_STATS,
    }


def _require_lesson(db: Session, lesson_no: int) -> KnowledgeLesson:
    lesson = db.query(KnowledgeLesson).filter_by(lesson_number=lesson_no).first()
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def _progress_dict(progress: Optional[LessonProgress], lesson_no: int) -> dict:
    if progress is None:
        return {"lesson_number": lesson_no}
    return {
        "lesson_number": lesson_no,
        "time_spent_seconds": progress.time_spent_seconds or 0,
        "view_count": progress.view_count or 0,
        "first_viewed_at": progress.first_viewed_at,
        "last_viewed_at": progress.last_viewed_at,
        "completed_at": progress.completed_at,
    }


@router.get("/lessons", response_model=List[KnowledgeLessonRead])
def list_syntax_lessons(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    stats = insights.lesson_stats(db, user_id)
    lessons = db.query(KnowledgeLesson).order_by(KnowledgeLesson.lesson_number.asc()).all()
    return [_serialize_lesson(lesson, stats) for lesson in lessons]


@router.get("/lessons/{lesson_no}", response_model=KnowledgeLessonDetail)
def get_syntax_lesson(lesson_no: int, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    lesson = _require_lesson(db, lesson_no)
    questions = [
        serialize_question(question)
        for question in db.query(TestQuestion).order_by(TestQuestion.test_id, TestQuestion.question_no)
        if curriculum.classify_question(question)["lesson_number"] == lesson_no
    ]
    notes = db.query(LessonNote).filter_by(user_id=user_id, lesson_number=lesson_no).order_by(LessonNote.id.desc()).all()
    progress = db.query(LessonProgress).filter_by(user_id=user_id, lesson_number=lesson_no).first()
    data = _serialize_lesson(lesson, insights.lesson_stats(db, user_id))
    data.update(content_md=lesson.content_md, questions=questions, notes=notes, progress=_progress_dict(progress, lesson_no))
    return data


@router.post("/lessons/{lesson_no}/progress", response_model=LessonProgressRead)
def update_lesson_progress(
    lesson_no: int,
    payload: LessonProgressUpdate,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Reading time (heartbeats from the lesson page) and completion; feeds the plan and study minutes."""
    _require_lesson(db, lesson_no)
    insights.get_or_create_user(db, user_id)
    now = timeutil.utcnow()
    progress = db.query(LessonProgress).filter_by(user_id=user_id, lesson_number=lesson_no).first()
    if progress is None:
        progress = LessonProgress(user_id=user_id, lesson_number=lesson_no, time_spent_seconds=0, view_count=0, first_viewed_at=now)
        db.add(progress)
    progress.last_viewed_at = now
    if payload.event == "view":
        progress.view_count = (progress.view_count or 0) + 1
    elif payload.event == "complete":
        progress.completed_at = progress.completed_at or now
    elif payload.event == "uncomplete":
        progress.completed_at = None
    if payload.seconds:
        progress.time_spent_seconds = (progress.time_spent_seconds or 0) + payload.seconds
        activity.track(db, user_id, "lesson", payload.seconds, ref=f"lesson:{lesson_no}", at=now)
    db.commit()
    db.refresh(progress)
    return _progress_dict(progress, lesson_no)


@router.get("/lessons/{lesson_no}/notes", response_model=List[LessonNoteRead])
def list_notes(lesson_no: int, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return db.query(LessonNote).filter_by(user_id=user_id, lesson_number=lesson_no).order_by(LessonNote.id.desc()).all()


@router.post("/lessons/{lesson_no}/notes", response_model=LessonNoteRead, status_code=201)
def add_note(lesson_no: int, payload: LessonNoteCreate, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    _require_lesson(db, lesson_no)
    insights.get_or_create_user(db, user_id)
    note = LessonNote(user_id=user_id, lesson_number=lesson_no, content=payload.content.strip(), source="user")
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/lessons/{lesson_no}/notes/{note_id}")
def delete_note(lesson_no: int, note_id: int, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    note = db.query(LessonNote).filter_by(id=note_id, user_id=user_id, lesson_number=lesson_no).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    db.delete(note)
    db.commit()
    return {"status": "deleted", "id": note_id}


@router.get("/paraphrases", response_model=List[ParaphrasePairRead])
def list_paraphrase_vault(
    query: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(ParaphrasePair)
    if query:
        pattern = f"%{query.lower()}%"
        q = q.filter(
            (ParaphrasePair.word_in_text.ilike(pattern))
            | (ParaphrasePair.word_in_answer.ilike(pattern))
            | (ParaphrasePair.meaning.ilike(pattern))
        )
    return q.order_by(ParaphrasePair.id.desc()).limit(limit).all()
