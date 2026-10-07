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


def is_test_mode() -> bool:
    return os.environ.get("TOEIC_SKIP_DOTENV") == "1" or os.environ.get("TESTING") == "1"


def active_user_id(token: str, db: Session) -> int:
    """Verify the JWT and that its account still exists and is not locked."""
    try:
        user_id = int(decode_access_token(token)["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
    row = db.query(User.id, User.is_active).filter(User.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")
    if row.is_active is False:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khoá, vui lòng liên hệ quản trị viên")
    return user_id


def current_user_id(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    user_id_query: Optional[int] = Query(None, alias="user_id", ge=1, include_in_schema=False),
    db: Session = Depends(get_db),
) -> int:
    """Authenticated user ID, or the shared guest learner (DEFAULT_USER_ID) when no token is sent.

    The `?user_id=` override only works in test/CLI mode: in production it would let anyone read
    or change another learner's data.
    """
    token = get_token_from_request(authorization, access_token)
    if token:
        return active_user_id(token, db)
    if user_id_query is not None and is_test_mode():
        return user_id_query
    return DEFAULT_USER_ID


def optional_learner_id(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    user_id_query: Optional[int] = Query(None, alias="user_id", ge=1, include_in_schema=False),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Logged-in user ID, or None for a guest whose actions must not be saved.

    Guests share the demo learner (DEFAULT_USER_ID) for reading; letting them write would mix every
    visitor's progress together. Test/CLI mode keeps the `?user_id=` / DEFAULT_USER_ID fallback.
    """
    token = get_token_from_request(authorization, access_token)
    if token:
        return active_user_id(token, db)
    if is_test_mode():
        return user_id_query if user_id_query is not None else DEFAULT_USER_ID
    return None


def require_authenticated_user(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    """Strict authentication dependency for endpoints requiring a verified account."""
    token = get_token_from_request(authorization, access_token)
    if not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục")
    return db.get(User, active_user_id(token, db))


def require_admin(user: User = Depends(require_authenticated_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên mới được truy cập")
    return user


def require_learner_user_id(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    user_id_query: Optional[int] = Query(None, alias="user_id", ge=1, include_in_schema=False),
    db: Session = Depends(get_db),
) -> int:
    """Authenticated user ID; requests without a token are rejected.

    In test/CLI mode (TOEIC_SKIP_DOTENV == '1' or TESTING == '1') it falls back to
    `?user_id=` or DEFAULT_USER_ID to keep the test-suite simple.
    """
    token = get_token_from_request(authorization, access_token)
    if token:
        return active_user_id(token, db)
    if is_test_mode():
        return user_id_query if user_id_query is not None else DEFAULT_USER_ID
    raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng tính năng này")
