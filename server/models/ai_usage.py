from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String

from server.database import Base
from server.utils.timeutil import utcnow


class AIUsageLog(Base):
    """One HTTP call to an AI provider. Calls made for one learner action share a request_id."""

    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(32), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # None: guest / system
    endpoint = Column(String(40), nullable=False)  # chat | translate | ai_fill | shadowing | ...
    provider = Column(String(20), nullable=False)
    model = Column(String(80), nullable=True)
    key_alias = Column(String(20), nullable=True)  # "gemini-2" -- never the key itself
    status = Column(String(20), nullable=False)  # ok | error | rate_limited
    http_status = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)

    __table_args__ = (Index("ix_ai_usage_user_created", "user_id", "created_at"),)


class AIKeyState(Base):
    """Admin switch for one configured key (the key itself stays in .env)."""

    __tablename__ = "ai_key_states"

    alias = Column(String(20), primary_key=True)
    disabled = Column(Boolean, nullable=False, default=False)
    note = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
