from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from server.database import Base

class KnowledgeLesson(Base):
    __tablename__ = "knowledge_lessons"

    id = Column(Integer, primary_key=True, index=True)
    lesson_number = Column(Integer, unique=True, nullable=False, index=True) # 1 -> 12
    title = Column(String(200), nullable=False)
    subtitle = Column(String(200), nullable=True)
    syntax_formula = Column(Text, nullable=True) # Mathematical grammar rules
    summary = Column(Text, nullable=True)
    content_html = Column(Text, nullable=False) # Full lesson content
    is_unlocked = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ParaphrasePair(Base):
    __tablename__ = "paraphrase_pairs"

    id = Column(Integer, primary_key=True, index=True)
    word_in_text = Column(String(100), nullable=False, index=True) # e.g. postpone
    word_in_answer = Column(String(100), nullable=False, index=True) # e.g. delay / defer
    meaning = Column(String(200), nullable=True)
    context_example = Column(Text, nullable=True)
    part_target = Column(String(20), default="Part 7")
    frequency = Column(String(20), default="High") # High, Extreme
