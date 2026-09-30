from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import KnowledgeLesson, ParaphrasePair
from server.schemas import KnowledgeLessonRead, ParaphrasePairRead

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Vault"])

@router.get("/lessons", response_model=List[KnowledgeLessonRead])
def list_syntax_lessons(db: Session = Depends(get_db)):
    return db.query(KnowledgeLesson).order_by(KnowledgeLesson.lesson_number.asc()).all()

@router.get("/lessons/{lesson_no}", response_model=KnowledgeLessonRead)
def get_syntax_lesson(lesson_no: int, db: Session = Depends(get_db)):
    lesson = db.query(KnowledgeLesson).filter_by(lesson_number=lesson_no).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

@router.get("/paraphrases", response_model=List[ParaphrasePairRead])
def list_paraphrase_vault(
    query: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    q = db.query(ParaphrasePair)
    if query:
        pattern = f"%{query.lower()}%"
        q = q.filter(
            (ParaphrasePair.word_in_text.ilike(pattern)) |
            (ParaphrasePair.word_in_answer.ilike(pattern)) |
            (ParaphrasePair.meaning.ilike(pattern))
        )
    return q.limit(limit).all()
