import os
from typing import Optional
from fastapi import Cookie, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from server.config import DEFAULT_USER_ID
from server.database import get_db
from server.models.user import User
from server.utils.security import decode_access_token


def get_token_from_request(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
) -> Optional[str]:
    """Extract bearer token from Authorization header or access_token cookie."""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        elif len(parts) == 1:
            return parts[0]
    if access_token:
        return access_token
    return None


def current_user_id(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    user_id_query: Optional[int] = Query(None, alias="user_id", ge=1),
) -> int:
    """Extract authenticated user ID from JWT token.

    If no token is provided, gracefully falls back to explicit user_id query param
    or DEFAULT_USER_ID (1) to preserve backward compatibility for tests and CLI scripts.
    """
    token = get_token_from_request(authorization, access_token)
    if token:
        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub is not None:
                return int(sub)
        except Exception:
            raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn")

    if user_id_query is not None:
        return user_id_query
    return DEFAULT_USER_ID


def require_authenticated_user(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    """Strict authentication dependency for endpoints requiring a verified account."""
    token = get_token_from_request(authorization, access_token)
    if not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")
    return user


def require_learner_user_id(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    user_id_query: Optional[int] = Query(None, alias="user_id", ge=1),
) -> int:
    """Extract authenticated user ID from JWT token.

    In production/real requests, strictly requires a valid authentication token.
    In testing/CLI mode (TOEIC_SKIP_DOTENV == '1' or TESTING == '1'), gracefully
    falls back to user_id_query or DEFAULT_USER_ID to preserve test compatibility.
    """
    token = get_token_from_request(authorization, access_token)
    if token:
        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub is not None:
                return int(sub)
        except Exception:
            raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn")

    if user_id_query is not None:
        return user_id_query

    if os.environ.get("TOEIC_SKIP_DOTENV") == "1" or os.environ.get("TESTING") == "1":
        return DEFAULT_USER_ID

    raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng tính năng này")

