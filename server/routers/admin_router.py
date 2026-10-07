"""Admin console API: every route requires a logged-in account with role "admin"."""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import require_admin
from server.models import User
from server.schemas import AdminAIKeyUpdate, AdminAIOverview, AdminUserDetail, AdminUserList, AdminUserUpdate
from server.services import admin_service, ai_agent_service, ai_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=AdminUserList)
def list_users(
    q: Optional[str] = Query(None, max_length=100),
    role: Optional[Literal["learner", "admin"]] = None,
    status: Optional[Literal["active", "locked"]] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return admin_service.list_users(db, q=q, role=role, status=status, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        return admin_service.get_user_detail(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/users/{user_id}", response_model=AdminUserDetail)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ai = {key: getattr(payload, key) for key in ("ai_unlimited", "ai_daily_quota") if key in payload.model_fields_set}
    try:
        result = admin_service.update_user(db, admin, user_id, payload.role, payload.is_active, ai)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except admin_service.AdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("admin %s updated user %s: %s", admin.id, user_id, payload.model_dump(exclude_none=True))
    return result


@router.get("/ai", response_model=AdminAIOverview)
def ai_overview(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """AI usage (requests, tokens, errors per day / feature / learner), key health and the default limits."""
    return {**ai_usage.overview(db, days), "provider": ai_agent_service.provider_status()}


@router.patch("/ai/keys/{alias}", response_model=AdminAIOverview)
def update_ai_key(alias: str, payload: AdminAIKeyUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Switch a configured key on/off by alias (the key itself never leaves .env)."""
    try:
        ai_usage.set_key_disabled(db, alias, payload.disabled, payload.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    logger.info("admin %s set AI key %s disabled=%s", admin.id, alias, payload.disabled)
    return {**ai_usage.overview(db), "provider": ai_agent_service.provider_status()}
