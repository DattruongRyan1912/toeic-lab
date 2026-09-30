from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from server.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, default="learner")
    target_score = Column(Integer, default=800)
    daily_goal_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    roadmaps = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")
    srs_cards = relationship("UserCardSRS", back_populates="user", cascade="all, delete-orphan")
    error_logs = relationship("ErrorLog", back_populates="user", cascade="all, delete-orphan")
    learning_gaps = relationship("AILearningGap", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("StudyReminder", back_populates="user", cascade="all, delete-orphan")
    test_submissions = relationship("UserTestSubmission", back_populates="user", cascade="all, delete-orphan")
