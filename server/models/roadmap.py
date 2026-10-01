from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from server.database import Base
from server.utils.timeutil import utcnow


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    total_weeks = Column(Integer, default=24)  # effective length (shrinks/grows with the exam date)
    base_total_weeks = Column(Integer, nullable=True)  # length the milestones were designed for
    current_week = Column(Integer, default=1)  # cached value; the API computes it from start_date
    start_date = Column(Date, nullable=True)  # falls back to created_at when empty
    status = Column(String(20), default="in_progress")
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    user = relationship("User", back_populates="roadmaps")
    tasks = relationship(
        "SprintTask",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="[SprintTask.week_number, SprintTask.id]",
    )


class SprintTask(Base):
    __tablename__ = "sprint_tasks"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False)
    phase = Column(Integer, default=1)  # 1: Foundation, 2: Mastery, 3: Mock tests
    week_number = Column(Integer, nullable=False, index=True)  # effective (rescaled) week
    base_week = Column(Integer, nullable=True)  # week in the original 24-week design
    category = Column(String(50), nullable=False)  # Listening, Reading, Syntax, Vocab, Test
    title = Column(Text, nullable=False)
    source = Column(String(20), nullable=True)  # seed | user | ai_mentor
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationship
    roadmap = relationship("Roadmap", back_populates="tasks")
