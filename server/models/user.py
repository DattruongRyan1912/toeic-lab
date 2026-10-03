from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from server.database import Base
from server.utils.timeutil import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, default="learner")
    display_name = Column(String(100), nullable=True)
    headline = Column(String(100), nullable=True)  # e.g. "Backend Engineer"
    target_score = Column(Integer, default=800)
    daily_goal_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=utcnow)

    # --- Authentication credentials (nullable for additive migration) ---
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    role = Column(String(20), default="learner", nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # --- Personalization profile (all nullable: added by the additive migration) ---
    exam_date = Column(Date, nullable=True)
    baseline_listening = Column(Integer, nullable=True)  # scaled 5-495 estimate when starting
    baseline_reading = Column(Integer, nullable=True)
    study_days = Column(String(20), nullable=True)  # "0,1,2,3,4,5" (Mon=0)
    new_cards_per_day = Column(Integer, nullable=True)  # overrides SRS_NEW_CARDS_PER_DAY
    explanation_style = Column(String(20), nullable=True)  # concise | detailed | socratic
    focus_parts = Column(String(100), nullable=True)  # "Part 5,Part 7"
    learning_goal_note = Column(Text, nullable=True)
    auto_adjust = Column(Boolean, nullable=True)  # allow the system to tune SRS load automatically
    onboarded_at = Column(DateTime, nullable=True)
    plan_generated_on = Column(Date, nullable=True)

    # Relationships
    roadmaps = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")
    srs_cards = relationship("UserCardSRS", back_populates="user", cascade="all, delete-orphan")
    error_logs = relationship("ErrorLog", back_populates="user", cascade="all, delete-orphan")
    learning_gaps = relationship("AILearningGap", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("StudyReminder", back_populates="user", cascade="all, delete-orphan")
    test_submissions = relationship("UserTestSubmission", back_populates="user", cascade="all, delete-orphan")
