from fastapi import Query

from server.config import DEFAULT_USER_ID


def current_user_id(
    user_id: int = Query(DEFAULT_USER_ID, ge=1, description="Single-learner mode (chưa có xác thực): mặc định user 1"),
) -> int:
    """Single seam for identifying the learner. Replace with real authentication when it lands."""
    return user_id
