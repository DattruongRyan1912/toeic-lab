from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- User & Dashboard Schemas ---
class UserRead(BaseModel):
    id: int
    username: str
    target_score: int
    daily_goal_minutes: int
    created_at: datetime
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    target_score: int
    roadmap_percent: int
    completed_tasks: int
    total_tasks: int
    srs_due_count: int
    srs_mastered_count: int
    total_flashcards: int
    total_errors: int
    rca_breakdown: Dict[str, int]
    top_learning_gaps: List[str]

# --- Roadmap & Tasks ---
class SprintTaskRead(BaseModel):
    id: int
    phase: int
    week_number: int
    category: str
    title: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class SprintTaskUpdate(BaseModel):
    is_completed: bool

class RoadmapRead(BaseModel):
    id: int
    title: str
    total_weeks: int
    current_week: int
    status: str
    tasks: List[SprintTaskRead] = []
    class Config:
        from_attributes = True

# --- Flashcards & SRS ---
class FlashcardRead(BaseModel):
    id: int
    category: str
    word: str
    ipa: Optional[str] = None
    word_type: Optional[str] = None
    meaning: str
    collocations: Optional[str] = None
    paraphrase_pair: Optional[str] = None
    example_sentence: str
    audio_word_url: Optional[str] = None
    audio_sentence_url: Optional[str] = None
    class Config:
        from_attributes = True

class UserCardSRSRead(BaseModel):
    id: int
    card_id: int
    flashcard: FlashcardRead
    repetition_count: int
    ease_factor: float
    interval_days: int
    state: str
    next_review_at: datetime
    class Config:
        from_attributes = True

class SRSReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=4, description="1: Again, 2: Hard, 3: Good, 4: Easy")

# --- Error Logs ---
class ErrorLogCreate(BaseModel):
    test_id: Optional[str] = "Practice"
    part: str # Part 1 -> Part 7
    question_no: Optional[int] = None
    error_type: str # VOCAB, GRAMMAR, PHONETICS, TRAP, TIME
    user_choice: Optional[str] = None
    correct_choice: Optional[str] = None
    question_content: Optional[str] = None
    image_url: Optional[str] = None
    root_cause: str
    key_rule_or_paraphrase: Optional[str] = None

class ErrorLogRead(BaseModel):
    id: int
    test_id: Optional[str]
    part: str
    question_no: Optional[int]
    error_type: str
    user_choice: Optional[str]
    correct_choice: Optional[str]
    question_content: Optional[str]
    image_url: Optional[str]
    root_cause: str
    key_rule_or_paraphrase: Optional[str]
    status: str
    review_count: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Knowledge & Lessons ---
class KnowledgeLessonRead(BaseModel):
    id: int
    lesson_number: int
    title: str
    subtitle: Optional[str]
    syntax_formula: Optional[str]
    summary: Optional[str]
    content_html: str
    is_unlocked: bool
    class Config:
        from_attributes = True

class ParaphrasePairRead(BaseModel):
    id: int
    word_in_text: str
    word_in_answer: str
    meaning: Optional[str]
    part_target: str
    frequency: str
    class Config:
        from_attributes = True

# --- AI & Vision ---
class AIChatRequest(BaseModel):
    message: str
    question_id: Optional[str] = None # Database Grounding Pointer (e.g. ETS2024_01_108)
    image_base64: Optional[str] = None # Vision OCR image data
    user_id: int = 1

class AIChatResponse(BaseModel):
    reply: str
    actions_taken: List[Dict[str, Any]] = [] # Details of tools invoked (e.g. auto-created error log)
    suggested_questions: List[str] = []

# --- Reminders ---
class StudyReminderRead(BaseModel):
    id: int
    reminder_type: str
    scheduled_time: str
    message: str
    is_active: bool
    class Config:
        from_attributes = True

class StudyReminderUpdate(BaseModel):
    scheduled_time: Optional[str] = None
    message: Optional[str] = None
    is_active: Optional[bool] = None
