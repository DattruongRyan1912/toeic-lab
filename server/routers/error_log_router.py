from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import ErrorLog
from server.schemas import ErrorLogRead, ErrorLogCreate

router = APIRouter(prefix="/api/error-logs", tags=["Error Logs (RCA)"])

@router.get("", response_model=List[ErrorLogRead])
def list_error_logs(
    user_id: int = 1,
    error_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ErrorLog).filter_by(user_id=user_id)
    if error_type:
        query = query.filter_by(error_type=error_type.upper())
    if status:
        query = query.filter_by(status=status)
    return query.order_by(ErrorLog.created_at.desc()).all()

@router.post("", response_model=ErrorLogRead)
def create_error_log(
    payload: ErrorLogCreate,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    err = ErrorLog(
        user_id=user_id,
        test_id=payload.test_id,
        part=payload.part,
        question_no=payload.question_no,
        error_type=payload.error_type.upper(),
        user_choice=payload.user_choice,
        correct_choice=payload.correct_choice,
        question_content=payload.question_content,
        image_url=payload.image_url,
        root_cause=payload.root_cause,
        key_rule_or_paraphrase=payload.key_rule_or_paraphrase,
        status="unresolved"
    )
    db.add(err)
    db.commit()
    db.refresh(err)
    return err

@router.patch("/{error_id}/status", response_model=ErrorLogRead)
def update_error_status(
    error_id: int,
    status: str = Query(..., pattern="^(unresolved|reviewed|mastered)$"),
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    err = db.query(ErrorLog).filter_by(id=error_id, user_id=user_id).first()
    if not err:
        raise HTTPException(status_code=404, detail="Error log not found")
    err.status = status
    if status in ["reviewed", "mastered"]:
        err.review_count += 1
    db.commit()
    db.refresh(err)
    return err

@router.delete("/{error_id}")
def delete_error_log(
    error_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    err = db.query(ErrorLog).filter_by(id=error_id, user_id=user_id).first()
    if not err:
        raise HTTPException(status_code=404, detail="Error log not found")
    db.delete(err)
    db.commit()
    return {"status": "deleted", "id": error_id}
