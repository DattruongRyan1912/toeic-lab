from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from server.database import Base
from server.utils.timeutil import utcnow


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id = Column(String(50), nullable=True, index=True)  # ETS2024_01
    part = Column(String(20), nullable=False, index=True)  # Part 1 -> Part 7
    question_no = Column(Integer, nullable=True)
    question_id = Column(Integer, nullable=True, index=True)  # TestQuestion.id when known
    error_type = Column(String(20), nullable=False, index=True)  # VOCAB, GRAMMAR, PHONETICS, TRAP, TIME
    user_choice = Column(String(10), nullable=True)
    correct_choice = Column(String(10), nullable=True)
    question_content = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)  # Vision photo upload
    root_cause = Column(Text, nullable=False)
    key_rule_or_paraphrase = Column(Text, nullable=True)
    topic = Column(String(150), nullable=True, index=True)  # trap tag, e.g. "Bẫy Vị Trí Trạng Từ"
    lesson_number = Column(Integer, nullable=True)  # syntax lesson that fixes this error
    source = Column(String(20), nullable=True, default="manual")  # manual | mock_test | ai_mentor
    status = Column(String(20), default="unresolved")  # unresolved, reviewed, mastered
    review_count = Column(Integer, default=0)
    # Spaced review of the mistake itself: stage 0 -> +1 day, 1 -> +3 days, 2 -> +7 days, 3 = mastered
    review_stage = Column(Integer, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationship
    user = relationship("User", back_populates="error_logs")


class AILearningGap(Base):
    """Derived from open error logs by services.insights.recompute_learning_gaps()."""

    __tablename__ = "ai_learning_gaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(150), nullable=False)
    error_count = Column(Integer, default=1)
    severity = Column(String(20), default="high")  # low, medium, high, critical
    lesson_number = Column(Integer, nullable=True)
    ai_recommendation = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utcnow)

    # Relationship
    user = relationship("User", back_populates="learning_gaps")
