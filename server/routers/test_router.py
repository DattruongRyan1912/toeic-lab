from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.models import MockTest, TestQuestion, UserTestSubmission
from server.schemas import (
    MockTestRead,
    QuestionRead,
    QuizSubmitRequest,
    QuizSubmitResult,
    ScoreCalcRequest,
    ScoreCalcResponse,
    SubmissionRead,
)
from server.services import curriculum, error_log_service, insights, practice_service, scoring

router = APIRouter(prefix="/api/tests", tags=["Benchmark Tests"])


def serialize_question(question: TestQuestion) -> dict:
    return {
        "id": question.id,
        "test_id": question.test_id,
        "part": question.part,
        "question_no": question.question_no,
        "sentence": question.sentence,
        "choice_a": question.choice_a,
        "choice_b": question.choice_b,
        "choice_c": question.choice_c,
        "choice_d": question.choice_d,
        "correct_choice": question.correct_choice,
        "explanation": question.explanation,
        "distractor_analysis": question.distractor_analysis,
        "paraphrase_pair": question.paraphrase_pair,
        "source": question.source or "seed",
        **curriculum.classify_question(question),
    }


@router.post("/calculate-score", response_model=ScoreCalcResponse)
def calculate_score(
    payload: ScoreCalcRequest,
    target: Optional[int] = Query(None, ge=10, le=990, description="Mặc định lấy mục tiêu trong hồ sơ học viên"),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if target is None:
        target = insights.get_or_create_user(db, user_id).target_score or 800
    return scoring.convert(payload.raw_listening, payload.raw_reading, target).as_dict()


@router.get("", response_model=List[MockTestRead])
def list_mock_tests(db: Session = Depends(get_db)):
    result = []
    for test in db.query(MockTest).order_by(MockTest.year.desc(), MockTest.test_id.asc()).all():
        parts = Counter(part for (part,) in db.query(TestQuestion.part).filter_by(test_id=test.test_id))
        result.append(
            {
                "id": test.id,
                "test_id": test.test_id,
                "name": test.name,
                "year": test.year,
                "publisher": test.publisher,
                "total_questions": test.total_questions,
                "available_questions": sum(parts.values()),
                "parts": dict(sorted(parts.items())),
            }
        )
    return result


@router.get("/submissions", response_model=List[SubmissionRead])
def list_submissions(
    limit: int = Query(20, ge=1, le=200),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    return (
        db.query(UserTestSubmission)
        .filter_by(user_id=user_id)
        .order_by(UserTestSubmission.submitted_at.desc(), UserTestSubmission.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/{test_id}/questions", response_model=List[QuestionRead])
def get_test_questions(
    test_id: str,
    part: Optional[str] = Query(None),
    lesson: Optional[int] = Query(None, ge=1, le=12, description="Chỉ lấy câu thuộc chuyên đề cú pháp này"),
    db: Session = Depends(get_db),
):
    query = db.query(TestQuestion).filter_by(test_id=test_id)
    if part:
        query = query.filter_by(part=curriculum.normalize_part(part) or part)
    questions = [serialize_question(q) for q in query.order_by(TestQuestion.question_no.asc()).all()]
    if lesson is not None:
        questions = [q for q in questions if q["lesson_number"] == lesson]
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this test")
    return questions


@router.get("/{test_id}/questions/{question_no}", response_model=QuestionRead)
def get_test_question(test_id: str, question_no: int, db: Session = Depends(get_db)):
    question = error_log_service.find_question(db, test_id, question_no)
    if question is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    return serialize_question(question)


@router.post("/{test_id}/submit", response_model=QuizSubmitResult)
def submit_quiz(
    test_id: str,
    payload: QuizSubmitRequest,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Grade a set from one test. Same pipeline as /api/practice/submit (attempts, error log, reviews, study time)."""
    answers = {str(key): value for key, value in payload.answers.items()}
    ids = list(dict.fromkeys(list(payload.question_ids) + [int(key) for key in answers if key.isdigit()]))
    if not ids:
        raise HTTPException(status_code=422, detail="Bài nộp không có câu hỏi nào")
    items = [
        practice_service.Answer(qid, answers.get(str(qid)), payload.answer_times.get(str(qid)))
        for qid in ids
    ]
    try:
        return practice_service.submit(
            db, user_id, items, mode=payload.mode, part=payload.part, lesson_number=payload.lesson_number,
            time_spent_seconds=payload.time_spent_seconds, log_errors=payload.log_errors, test_id=test_id,
        )
    except practice_service.PracticeError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
