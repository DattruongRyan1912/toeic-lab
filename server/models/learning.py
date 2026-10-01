"""Learning-process tracking and personalization tables (all scoped to a learner)."""
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from server.database import Base
from server.utils.timeutil import utcnow


class QuestionAttempt(Base):
    """One answer to one question: source of truth for skill mastery, pace and error reviews."""

    __tablename__ = "question_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    submission_id = Column(Integer, nullable=True, index=True)
    choice = Column(String(1), nullable=True)  # None = left blank
    is_correct = Column(Boolean, nullable=False, default=False)
    time_ms = Column(Integer, nullable=True)
    mode = Column(String(20), nullable=True)  # practice | study | exam | review | smart
    # Copied from the question at answer time so history survives question edits/deletion.
    part = Column(String(20), nullable=True)
    lesson_number = Column(Integer, nullable=True)
    error_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)


class StudySession(Base):
    """Study time per activity. Consecutive events of the same kind within 20 minutes are merged."""

    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)  # srs | practice | review | lesson | mentor | listening | reading | other
    ref = Column(String(50), nullable=True)  # e.g. "lesson:2", "submission:15"
    started_at = Column(DateTime, default=utcnow, index=True)
    last_activity_at = Column(DateTime, default=utcnow)
    duration_seconds = Column(Integer, default=0)
    items = Column(Integer, default=0)
    correct = Column(Integer, default=0)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_number", name="uq_user_lesson"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_number = Column(Integer, nullable=False)
    time_spent_seconds = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    first_viewed_at = Column(DateTime, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class LessonNote(Base):
    """Personal notes on a lesson, written by the learner or by the AI mentor."""

    __tablename__ = "lesson_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_number = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    source = Column(String(20), default="user")  # user | ai_mentor
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class LearnerMemory(Base):
    """Long-term facts about the learner that personalize every AI conversation."""

    __tablename__ = "learner_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(30), default="other")  # goal | preference | struggle | strength | context | other
    content = Column(Text, nullable=False)
    source = Column(String(20), default="user")  # user | ai_mentor | onboarding
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class StudyPlanItem(Base):
    """One task of the adaptive daily plan. Activity-based kinds complete themselves (status derived on read)."""

    __tablename__ = "study_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date = Column(Date, nullable=False, index=True)
    kind = Column(String(30), nullable=False)  # srs | error_review | lesson | practice | smart | mock | listening | ai_generate | custom
    title = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)  # why the planner chose it (shown to the learner)
    lesson_number = Column(Integer, nullable=True)
    part = Column(String(20), nullable=True)
    target_count = Column(Integer, nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    priority = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending | done | skipped (manual)
    source = Column(String(20), default="planner")  # planner | user | ai_mentor
    ref = Column(String(50), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class AIActionLog(Base):
    """Audit trail of every data change made through agent tools, with the data needed to undo it."""

    __tablename__ = "ai_action_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tool = Column(String(60), nullable=False)
    source = Column(String(20), default="ai_mentor")  # ai_mentor | user | coach
    summary = Column(Text, nullable=True)
    args_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    undo_json = Column(Text, nullable=True)
    status = Column(String(20), default="applied")  # applied | undone
    created_at = Column(DateTime, default=utcnow, index=True)
    undone_at = Column(DateTime, nullable=True)
