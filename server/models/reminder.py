from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from server.database import Base

class StudyReminder(Base):
    __tablename__ = "study_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reminder_type = Column(String(50), nullable=False) # daily_study, review_error_log, srs_due
    scheduled_time = Column(String(10), nullable=False, default="21:00") # "HH:MM" 24h format
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="reminders")
