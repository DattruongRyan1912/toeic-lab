from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.database import get_db
from server.models import MockTest, TestQuestion

router = APIRouter(prefix="/api/tests", tags=["Benchmark Tests"])

class ScoreCalcRequest(BaseModel):
    raw_listening: int
    raw_reading: int

class ScoreCalcResponse(BaseModel):
    raw_listening: int
    raw_reading: int
    scaled_listening: int
    scaled_reading: int
    total_score: int
    cefr_level: str
    target_gap: int

# ETS Standard Score Conversion Curve Table
def convert_toeic_score(l_raw: int, r_raw: int, target: int = 800) -> ScoreCalcResponse:
    # Listening curve approximation
    if l_raw >= 96: l_scale = 495
    elif l_raw >= 90: l_scale = 460 + (l_raw - 90) * 5
    elif l_raw >= 80: l_scale = 395 + (l_raw - 80) * 6
    elif l_raw >= 70: l_scale = 330 + (l_raw - 70) * 6
    elif l_raw >= 60: l_scale = 270 + (l_raw - 60) * 6
    elif l_raw >= 50: l_scale = 220 + (l_raw - 50) * 5
    else: l_scale = max(5, l_raw * 4)

    # Reading curve approximation
    if r_raw >= 97: r_scale = 495
    elif r_raw >= 90: r_scale = 450 + (r_raw - 90) * 6
    elif r_raw >= 80: r_scale = 385 + (r_raw - 80) * 6
    elif r_raw >= 70: r_scale = 325 + (r_raw - 70) * 6
    elif r_raw >= 60: r_scale = 260 + (r_raw - 60) * 6
    elif r_raw >= 50: r_scale = 205 + (r_raw - 50) * 5
    else: r_scale = max(5, r_raw * 4)

    total = min(990, l_scale + r_scale)

    # CEFR Level
    if total >= 945: cefr = "C1 - Advanced"
    elif total >= 785: cefr = "B2 - Working Proficiency (Target 800+)"
    elif total >= 550: cefr = "B1 - Limited Working"
    elif total >= 225: cefr = "A2 - Elementary"
    else: cefr = "A1 - Beginner"

    gap = max(0, target - total)
    return ScoreCalcResponse(
        raw_listening=l_raw,
        raw_reading=r_raw,
        scaled_listening=l_scale,
        scaled_reading=r_scale,
        total_score=total,
        cefr_level=cefr,
        target_gap=gap
    )

@router.post("/calculate-score", response_model=ScoreCalcResponse)
def calculate_score(payload: ScoreCalcRequest, target: int = 800):
    return convert_toeic_score(payload.raw_listening, payload.raw_reading, target)

@router.get("")
def list_mock_tests(db: Session = Depends(get_db)):
    return db.query(MockTest).all()

@router.get("/{test_id}/questions")
def get_test_questions(
    test_id: str,
    part: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(TestQuestion).filter_by(test_id=test_id)
    if part:
        q = q.filter_by(part=part)
    questions = q.order_by(TestQuestion.question_no.asc()).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this test")
    return questions
