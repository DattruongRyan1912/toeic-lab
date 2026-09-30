from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from server.database import Base

class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id = Column(String(50), nullable=True, index=True) # ETS2024_01
    part = Column(String(20), nullable=False, index=True) # Part 1 -> Part 7
    question_no = Column(Integer, nullable=True)
    error_type = Column(String(20), nullable=False, index=True) # VOCAB, GRAMMAR, PHONETICS, TRAP, TIME
    user_choice = Column(String(10), nullable=True)
    correct_choice = Column(String(10), nullable=True)
    question_content = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True) # Vision photo upload
    root_cause = Column(Text, nullable=False)
    key_rule_or_paraphrase = Column(Text, nullable=True)
    status = Column(String(20), default="unresolved") # unresolved, reviewed, mastered
    review_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="error_logs")

class AILearningGap(Base):
    __tablename__ = "ai_learning_gaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(150), nullable=False) # e.g. "Bẫy Similar Sound Part 2", "Rút gọn mệnh đề quan hệ"
    error_count = Column(Integer, default=1)
    severity = Column(String(20), default="high") # low, medium, high, critical
    ai_recommendation = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="learning_gaps")
