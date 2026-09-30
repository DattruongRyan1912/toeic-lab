from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from server.database import Base

class MockTest(Base):
    __tablename__ = "mock_tests"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String(50), unique=True, index=True, nullable=False) # e.g. ETS2024_01
    name = Column(String(150), nullable=False)
    year = Column(Integer, default=2024)
    publisher = Column(String(50), default="ETS") # ETS, Hackers, YBM
    total_questions = Column(Integer, default=200)

    # Relationships
    questions = relationship("TestQuestion", back_populates="test", cascade="all, delete-orphan")

class TestQuestion(Base):
    __tablename__ = "test_questions"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String(50), ForeignKey("mock_tests.test_id", ondelete="CASCADE"), nullable=False, index=True)
    part = Column(String(20), nullable=False, index=True) # Part 1 -> Part 7
    question_no = Column(Integer, nullable=False)
    sentence = Column(Text, nullable=False)
    choice_a = Column(Text, nullable=False)
    choice_b = Column(Text, nullable=False)
    choice_c = Column(Text, nullable=False)
    choice_d = Column(Text, nullable=True) # Part 2 only has A B C
    correct_choice = Column(String(5), nullable=False)
    explanation = Column(Text, nullable=True)
    distractor_analysis = Column(Text, nullable=True) # Explanation of why other choices are traps
    paraphrase_pair = Column(Text, nullable=True)

    # Relationship
    test = relationship("MockTest", back_populates="questions")

class UserTestSubmission(Base):
    __tablename__ = "user_test_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(String(50), nullable=False, index=True)
    raw_listening = Column(Integer, default=0)
    raw_reading = Column(Integer, default=0)
    scaled_listening = Column(Integer, default=0)
    scaled_reading = Column(Integer, default=0)
    total_scaled_score = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="test_submissions")
