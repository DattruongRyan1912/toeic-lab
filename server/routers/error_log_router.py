from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id, require_learner_user_id
from server.models import ErrorLog, TestQuestion
from server.schemas import ErrorLogCreate, ErrorLogRead, ErrorLogUpdate
from server.services import error_log_service, insights

router = APIRouter(prefix="/api/error-logs", tags=["Error Logs (RCA)"])


def _get_owned(db: Session, error_id: int, user_id: int) -> ErrorLog:
    log = db.query(ErrorLog).filter_by(id=error_id, user_id=user_id).first()
    if log is None:
        raise HTTPException(status_code=404, detail="Error log not found")
    return log


@router.get("", response_model=List[ErrorLogRead])
def list_error_logs(
    error_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(unresolved|reviewed|mastered)$"),
    source: Optional[str] = Query(None, pattern="^(manual|mock_test|ai_mentor)$"),
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    query = db.query(ErrorLog).filter_by(user_id=user_id)
    if error_type:
        query = query.filter_by(error_type=error_type.upper())
    if status:
        query = query.filter_by(status=status)
    if source:
        query = query.filter_by(source=source)
    return query.order_by(ErrorLog.created_at.desc(), ErrorLog.id.desc()).all()


@router.post("", response_model=ErrorLogRead, status_code=201)
def create_error_log(payload: ErrorLogCreate, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    fields = payload.model_dump()
    question = None
    if payload.question_id:
        question = db.get(TestQuestion, payload.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi trong ngân hàng đề")
    else:
        question = error_log_service.find_question(db, payload.test_id, payload.question_no)
    error_log_service.enrich_from_question(fields, question)
    fields["source"] = "manual"
    # One log per question: a second entry for a question already logged re-opens that log with the
    # learner's own analysis (two logs for one question used to leave one stuck "due" forever).
    log, status = error_log_service.upsert_error_log(db, user_id, fields, dedupe=bool(fields.get("question_id")))
    if status != "created":
        log.error_type = (fields.get("error_type") or log.error_type).upper()
        log.root_cause = fields.get("root_cause") or log.root_cause
        log.key_rule_or_paraphrase = fields.get("key_rule_or_paraphrase") or log.key_rule_or_paraphrase
        log.source = "manual"
    db.commit()
    insights.recompute_learning_gaps(db, user_id)
    db.refresh(log)
    return log


@router.patch("/{error_id}", response_model=ErrorLogRead)
def update_error_log(
    error_id: int,
    payload: ErrorLogUpdate,
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    log = _get_owned(db, error_id, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("error_type"):
        log.error_type = changes["error_type"]
    if changes.get("root_cause"):
        log.root_cause = changes["root_cause"].strip()
    if "key_rule_or_paraphrase" in changes:
        log.key_rule_or_paraphrase = (changes["key_rule_or_paraphrase"] or "").strip() or None
    if changes.get("status"):
        error_log_service.apply_status(log, changes["status"])  # keeps the 1-3-7 review schedule consistent
    if {"root_cause", "key_rule_or_paraphrase", "error_type"} & changes.keys():
        log.source = "manual"  # the learner owns this analysis now; automated runs won't overwrite it
    db.commit()
    insights.recompute_learning_gaps(db, user_id)
    db.refresh(log)
    return log


@router.patch("/{error_id}/status", response_model=ErrorLogRead)
def update_error_status(
    error_id: int,
    status: str = Query(..., pattern="^(unresolved|reviewed|mastered)$"),
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    """Kept for the legacy UI; equivalent to PATCH /{error_id} with {"status": ...}."""
    log = _get_owned(db, error_id, user_id)
    error_log_service.apply_status(log, status)
    db.commit()
    insights.recompute_learning_gaps(db, user_id)
    db.refresh(log)
    return log


@router.delete("/{error_id}")
def delete_error_log(error_id: int, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    log = _get_owned(db, error_id, user_id)
    db.delete(log)
    db.commit()
    insights.recompute_learning_gaps(db, user_id)
    return {"status": "deleted", "id": error_id}
