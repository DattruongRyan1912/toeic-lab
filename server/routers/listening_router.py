from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.schemas import (
    DictationCheckRequest,
    DictationCheckResponse,
    ListeningExercise,
    ListeningTrackRequest,
    ShadowingEvaluateRequest,
    ShadowingEvaluateResponse,
)
from server.services import listening_service

router = APIRouter(prefix="/api/listening", tags=["Listening (Dictation & Shadowing)"])


@router.get("/exercises", response_model=List[ListeningExercise])
def get_listening_exercises(
    part: Optional[str] = Query(None, description="Part 1, Part 2, Part 3, or Part 4"),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Retrieve listening exercises for dictation and shadowing."""
    return listening_service.list_exercises(db, part=part, difficulty=difficulty, limit=limit)


@router.post("/check-dictation", response_model=DictationCheckResponse)
def check_dictation(
    payload: DictationCheckRequest,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Evaluate learner's typed transcription with token-level diff and phonetic cues."""
    target = payload.target_transcript
    if not target:
        from server.models import TestQuestion
        from fastapi import HTTPException
        q = db.query(TestQuestion).filter(TestQuestion.id == payload.question_id).first()
        if not q or not q.sentence:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi luyện nghe")
        target = q.sentence

    result = listening_service.diff_transcription(payload.learner_text, target)
    if payload.time_spent_seconds and payload.time_spent_seconds > 0:
        listening_service.track_listening_activity(db, user_id, payload.time_spent_seconds)
    return result


@router.post("/track")
def track_listening(
    payload: ListeningTrackRequest,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Track listening activity time (adds to daily study minutes for 'listening')."""
    return listening_service.track_listening_activity(db, user_id, payload.seconds)


@router.post("/evaluate-shadowing", response_model=ShadowingEvaluateResponse)
async def evaluate_shadowing(
    payload: ShadowingEvaluateRequest,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Evaluate learner's spoken shadowing audio/transcript with AI scoring, word analysis, and coaching tips."""
    from server.services import voice_coach_service
    res = await voice_coach_service.evaluate_shadowing_speech(
        target_sentence=payload.target_sentence,
        user_transcript=payload.user_transcript,
        audio_base64=payload.audio_base64,
        phonetic_cues=payload.phonetic_cues,
        accent=payload.accent,
    )
    listening_service.track_listening_activity(db, user_id, 15)
    return res
