from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from server.database import Base

class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    total_weeks = Column(Integer, default=24)
    current_week = Column(Integer, default=1)
    status = Column(String(20), default="in_progress")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="roadmaps")
    tasks = relationship("SprintTask", back_populates="roadmap", cascade="all, delete-orphan", order_by="SprintTask.week_number")

class SprintTask(Base):
    __tablename__ = "sprint_tasks"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False)
    phase = Column(Integer, default=1) # 1: Foundation (1-8), 2: Mastery (9-16), 3: Mock Test (17-24)
    week_number = Column(Integer, nullable=False, index=True)
    category = Column(String(50), nullable=False) # Listening, Reading, Syntax, Vocab, Test
    title = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationship
    roadmap = relationship("Roadmap", back_populates="tasks")
