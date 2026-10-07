from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import optional_learner_id
from server.models import TestQuestion
from server.schemas import (
    DictationCheckRequest,
    DictationCheckResponse,
    ListeningExercise,
    ListeningTrackRequest,
    ShadowingEvaluateRequest,
    ShadowingEvaluateResponse,
)
from server.services import listening_service
from server.utils import rate_limit

router = APIRouter(prefix="/api/listening", tags=["Listening (Dictation & Shadowing)"])


@router.get("/exercises", response_model=List[ListeningExercise])
def get_listening_exercises(
    part: Optional[str] = Query(None, description="Part 1, Part 2, Part 3, or Part 4"),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve listening exercises for dictation and shadowing."""
    return listening_service.list_exercises(db, part=part, difficulty=difficulty, limit=limit)


@router.post("/check-dictation", response_model=DictationCheckResponse)
def check_dictation(
    payload: DictationCheckRequest,
    user_id: Optional[int] = Depends(optional_learner_id),
    db: Session = Depends(get_db),
):
    """Evaluate learner's typed transcription with token-level diff and phonetic cues."""
    # The bank question is the reference whenever it exists (Part 2: question + the three responses).
    q = db.get(TestQuestion, payload.question_id)
    target = listening_service.dictation_target(q) if q is not None and q.sentence else payload.target_transcript
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi luyện nghe")

    result = listening_service.diff_transcription(payload.learner_text, target)
    if payload.time_spent_seconds and payload.time_spent_seconds > 0:
        listening_service.track_listening_activity(db, user_id, payload.time_spent_seconds)
    return result


@router.post("/track")
def track_listening(
    payload: ListeningTrackRequest,
    user_id: Optional[int] = Depends(optional_learner_id),
    db: Session = Depends(get_db),
):
    """Track listening activity time (adds to daily study minutes for 'listening')."""
    return listening_service.track_listening_activity(db, user_id, payload.seconds)


@router.post("/evaluate-shadowing", response_model=ShadowingEvaluateResponse, dependencies=[Depends(rate_limit.limit_ai)])
async def evaluate_shadowing(payload: ShadowingEvaluateRequest):
    """Evaluate learner's spoken shadowing audio/transcript with AI scoring, word analysis, and coaching tips."""
    from server.services import voice_coach_service
    res = await voice_coach_service.evaluate_shadowing_speech(
        target_sentence=payload.target_sentence,
        user_transcript=payload.user_transcript,
        audio_base64=payload.audio_base64,
        phonetic_cues=payload.phonetic_cues,
        accent=payload.accent,
    )
    return res  # study time is tracked by the page heartbeat, not a flat bonus per evaluation
