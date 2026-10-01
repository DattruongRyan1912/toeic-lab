from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from server.database import Base
from server.utils.timeutil import utcnow


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    word = Column(String(100), nullable=False, index=True)
    ipa = Column(String(100), nullable=True)
    word_type = Column(String(50), nullable=True)  # verb, noun, adjective, adverb
    meaning = Column(Text, nullable=False)
    collocations = Column(Text, nullable=True)
    paraphrase_pair = Column(Text, nullable=True)
    example_sentence = Column(Text, nullable=False)
    audio_word_url = Column(String(255), nullable=True)
    audio_sentence_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    user_srs_records = relationship("UserCardSRS", back_populates="flashcard", cascade="all, delete-orphan")


class UserCardSRS(Base):
    __tablename__ = "user_flashcard_srs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id = Column(Integer, ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False, index=True)

    # SM-2 Spaced Repetition Fields
    repetition_count = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)  # Minimum 1.3
    interval_days = Column(Integer, default=1)
    state = Column(String(20), default="new")  # new, learning, review, mastered
    next_review_at = Column(DateTime, default=utcnow, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_user_card"),)

    # Relationships
    user = relationship("User", back_populates="srs_cards")
    flashcard = relationship("Flashcard", back_populates="user_srs_records")


class SRSReviewLog(Base):
    """One row per review. UserCardSRS only keeps the latest state, this keeps history
    so the dashboard can compute daily activity, streaks and the daily new-card quota."""

    __tablename__ = "srs_review_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id = Column(Integer, nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    prev_state = Column(String(20), nullable=True)
    new_state = Column(String(20), nullable=True)
    interval_days = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # time spent on the card (reported by the client)
    reviewed_at = Column(DateTime, default=utcnow, index=True)
