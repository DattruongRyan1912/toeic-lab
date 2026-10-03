from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from server.services.curriculum import normalize_part

ErrorType = Literal["VOCAB", "GRAMMAR", "PHONETICS", "TRAP", "TIME"]
ErrorStatus = Literal["unresolved", "reviewed", "mastered"]
HHMM_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _upper_choice(value):
    """Accept "a", "(A)", "A. clear" -> "A"; empty -> None; anything else is rejected."""
    if value is None or not str(value).strip():
        return None
    from server.services.error_log_service import normalize_choice

    choice = normalize_choice(value)
    if choice is None:
        raise ValueError("Đáp án phải là A, B, C hoặc D")
    return choice


# --------------------------------------------------------------------------- users
ExplanationStyle = Literal["concise", "detailed", "socratic"]


class UserRead(ORMModel):
    id: int
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    headline: Optional[str] = None
    role: Optional[str] = "learner"
    avatar_url: Optional[str] = None
    target_score: int
    daily_goal_minutes: int
    target_cefr: Optional[str] = None
    created_at: datetime
    # personalization profile
    exam_date: Optional[date] = None
    days_to_exam: Optional[int] = None
    baseline_listening: Optional[int] = None
    baseline_reading: Optional[int] = None
    study_days: List[int] = []
    new_cards_per_day: Optional[int] = None
    effective_new_cards_per_day: int = 15
    explanation_style: str = "detailed"
    focus_parts: List[str] = []
    learning_goal_note: Optional[str] = None
    auto_adjust: bool = True
    onboarded: bool = False
    onboarded_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    headline: Optional[str] = Field(None, max_length=100)
    target_score: Optional[int] = Field(None, ge=10, le=990)
    daily_goal_minutes: Optional[int] = Field(None, ge=10, le=600)
    exam_date: Optional[date] = None
    baseline_listening: Optional[int] = Field(None, ge=5, le=495)
    baseline_reading: Optional[int] = Field(None, ge=5, le=495)
    study_days: Optional[List[int]] = Field(None, min_length=1, max_length=7)
    new_cards_per_day: Optional[int] = Field(None, ge=0, le=100)
    explanation_style: Optional[ExplanationStyle] = None
    focus_parts: Optional[List[str]] = Field(None, max_length=7)
    learning_goal_note: Optional[str] = Field(None, max_length=2000)
    auto_adjust: Optional[bool] = None


class OnboardingRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    headline: Optional[str] = Field(None, max_length=100)
    target_score: int = Field(800, ge=10, le=990)
    exam_date: Optional[date] = None
    baseline_listening: Optional[int] = Field(None, ge=5, le=495)
    baseline_reading: Optional[int] = Field(None, ge=5, le=495)
    daily_goal_minutes: int = Field(45, ge=10, le=600)
    study_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5], min_length=1, max_length=7)
    new_cards_per_day: Optional[int] = Field(None, ge=0, le=100)
    explanation_style: ExplanationStyle = "detailed"
    focus_parts: List[str] = Field(default_factory=list, max_length=7)
    weak_areas: Optional[str] = Field(None, max_length=1000, description="Tự nhận xét điểm yếu (lưu thành trí nhớ cho AI)")
    learning_goal_note: Optional[str] = Field(None, max_length=2000)


# --------------------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    target_score: int = Field(800, ge=10, le=990)


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=100)


class AuthUser(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    headline: Optional[str] = None
    target_score: int = 800
    target_cefr: Optional[str] = None
    role: Optional[str] = "learner"
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


# --------------------------------------------------------------------------- tests & submissions
class SubmissionRead(ORMModel):
    id: int
    test_id: str
    part: Optional[str] = None
    mode: Optional[str] = None
    lesson_number: Optional[int] = None
    correct_count: Optional[int] = None
    total_questions: Optional[int] = None
    accuracy: Optional[float] = None
    scaled_listening: Optional[int] = None
    scaled_reading: Optional[int] = None
    total_scaled_score: Optional[int] = None
    time_spent_seconds: Optional[int] = None
    submitted_at: datetime


class MockTestRead(BaseModel):
    id: int
    test_id: str
    name: str
    year: Optional[int] = None
    publisher: Optional[str] = None
    total_questions: Optional[int] = None
    available_questions: int
    category: Optional[str] = "mock"
    parts: Dict[str, int]


class ScoreCalcRequest(BaseModel):
    raw_listening: int = Field(..., ge=0, le=100)
    raw_reading: int = Field(..., ge=0, le=100)


class ScoreCalcResponse(BaseModel):
    raw_listening: int
    raw_reading: int
    scaled_listening: int
    scaled_reading: int
    total_score: int
    cefr_code: str
    cefr_level: str
    cefr_description: str
    target_score: int
    target_gap: int
    suggested_gain_listening: int
    suggested_gain_reading: int
    recommendations: List[str]


class QuestionRead(BaseModel):
    id: int
    test_id: str
    part: str
    question_no: int
    sentence: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: Optional[str] = None
    correct_choice: str
    explanation: Optional[str] = None
    distractor_analysis: Optional[str] = None
    paraphrase_pair: Optional[str] = None
    trap_tag: Optional[str] = None
    error_type: str
    lesson_number: Optional[int] = None
    image_url: Optional[str] = None
    source: Optional[str] = None


PracticeMode = Literal["practice", "study", "exam", "review", "smart"]


class QuizSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict, description="question_id -> A/B/C/D")
    question_ids: List[int] = Field(default_factory=list, max_length=200, description="Toàn bộ câu đã hiển thị (kể cả bỏ trống)")
    answer_times: Dict[str, int] = Field(default_factory=dict, description="question_id -> ms đã dùng cho câu đó")
    mode: PracticeMode = "practice"
    part: Optional[str] = Field(None, max_length=30)
    lesson_number: Optional[int] = Field(None, ge=1, le=12)
    time_spent_seconds: int = Field(0, ge=0, le=36000)
    log_errors: bool = True


class PracticeAnswer(BaseModel):
    question_id: int
    choice: Optional[str] = Field(None, max_length=20)
    time_ms: Optional[int] = Field(None, ge=0, le=3_600_000)


class PracticeSubmitRequest(BaseModel):
    answers: List[PracticeAnswer] = Field(..., min_length=1, max_length=200)
    mode: PracticeMode = "practice"
    part: Optional[str] = Field(None, max_length=30)
    lesson_number: Optional[int] = Field(None, ge=1, le=12)
    time_spent_seconds: int = Field(0, ge=0, le=36000)
    log_errors: bool = True


class PracticeQuestion(QuestionRead):
    reason: Optional[str] = None
    error_log_id: Optional[int] = None
    review_stage: Optional[int] = None
    difficulty: Optional[str] = None


class QuestionResult(BaseModel):
    question_id: int
    question_no: int
    part: str
    user_choice: Optional[str] = None
    correct_choice: str
    is_correct: bool
    error_type: str
    trap_tag: Optional[str] = None
    lesson_number: Optional[int] = None
    error_log_id: Optional[int] = None
    test_id: Optional[str] = None
    time_ms: Optional[int] = None
    review_outcome: Optional[str] = None


class LearningGapRead(BaseModel):
    id: int
    topic: str
    error_count: int
    severity: str
    lesson_number: Optional[int] = None
    lesson_title: Optional[str] = None
    ai_recommendation: Optional[str] = None


class QuizSubmitResult(BaseModel):
    submission_id: int
    test_id: str
    part: Optional[str] = None
    lesson_number: Optional[int] = None
    correct_count: int
    total_questions: int
    unanswered: int
    accuracy: float
    scaled_listening: Optional[int] = None
    scaled_reading: Optional[int] = None
    errors_logged: int
    mode: str = "practice"
    reviews_advanced: int = 0
    errors_mastered: int = 0
    avg_time_seconds: Optional[float] = None
    time_spent_seconds: int = 0
    results: List[QuestionResult]
    learning_gaps: List[LearningGapRead]


# --------------------------------------------------------------------------- dashboard
class DayActivity(BaseModel):
    date: date
    weekday: str
    is_today: bool
    is_future: bool
    srs_reviews: int
    questions_answered: int
    errors_logged: int
    tasks_completed: int
    mentor_questions: int
    minutes: int = 0
    total: int
    active: bool


class TodayTask(BaseModel):
    key: str
    title: str
    tag: str
    href: str
    done: bool
    detail: Optional[str] = None
    kind: str = "custom"
    status: str = "pending"
    auto: bool = False
    reason: Optional[str] = None
    estimated_minutes: Optional[int] = 0
    progress: Optional[int] = None
    target: Optional[int] = None
    plan_item_id: Optional[int] = None
    lesson_number: Optional[int] = None


class PredictedScoreBrief(BaseModel):
    total: int
    low: int
    high: int
    listening: int
    reading: int
    confidence: float
    basis_listening: str
    basis_reading: str
    confidence_level: Optional[str] = "low"
    questions_needed_to_narrow: Optional[int] = 0


class LessonBrief(BaseModel):
    lesson_number: int
    title: str
    subtitle: Optional[str] = None
    syntax_formula: Optional[str] = None
    summary: Optional[str] = None
    reason: str
    question_count: int
    accuracy: Optional[float] = None
    mastery: Optional[float] = None
    status: str


class DashboardStats(BaseModel):
    # Legacy fields (still read by docs/index.html)
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
    # Connected fields
    display_name: str
    headline: Optional[str] = None
    target_cefr: str
    daily_goal_minutes: int
    current_week: int
    total_weeks: int
    current_phase: int
    roadmap_title: Optional[str] = None
    srs_review_due: int
    srs_new_available: int
    srs_reviewed_today: int
    srs_learning_count: int
    open_errors: int
    learning_gaps: List[LearningGapRead]
    streak_days: int
    activity_week: List[DayActivity]
    today_tasks: List[TodayTask]
    recommended_lesson: Optional[LessonBrief] = None
    latest_submission: Optional[SubmissionRead] = None
    srs_new_cards_per_day: int = 15
    error_reviews_due: int = 0
    study_minutes_today: int = 0
    study_minutes_week: int = 0
    today_plan_minutes: int = 0
    predicted_score: Optional[PredictedScoreBrief] = None
    onboarded: bool = False
    exam_date: Optional[date] = None
    days_to_exam: Optional[int] = None
    total_attempts: int = 0


# --------------------------------------------------------------------------- roadmap
class SprintTaskRead(ORMModel):
    id: int
    phase: int
    week_number: int
    category: str
    title: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    base_week: Optional[int] = None
    source: Optional[str] = None
    auto_met: bool = False
    evidence: Optional[str] = None


class SprintTaskUpdate(BaseModel):
    is_completed: bool


class RoadmapRead(BaseModel):
    id: int
    title: str
    total_weeks: int
    base_total_weeks: Optional[int] = None
    exam_date: Optional[date] = None
    current_week: int
    current_phase: int
    start_date: date
    status: str
    progress_percent: int
    completed_tasks: int
    total_tasks: int
    tasks: List[SprintTaskRead] = []


class RoadmapUpdate(BaseModel):
    start_date: Optional[date] = None
    title: Optional[str] = Field(None, min_length=3, max_length=150)


# --------------------------------------------------------------------------- flashcards & SRS
class FlashcardCreate(BaseModel):
    category: str = Field("General Business", max_length=100)
    word: str = Field(..., min_length=1, max_length=100)
    ipa: Optional[str] = Field(None, max_length=100)
    word_type: Optional[str] = Field(None, max_length=50)
    meaning: str = Field(..., min_length=1)
    collocations: Optional[str] = None
    paraphrase_pair: Optional[str] = None
    example_sentence: str = Field(..., min_length=1)
    example_translation: Optional[str] = None


class AIFillVocabRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    context: Optional[str] = Field(None, max_length=1000)


class AIFillVocabResponse(BaseModel):
    word: str
    ipa: str
    word_type: str
    category: str
    meaning: str
    collocations: str
    paraphrase_pair: str
    example_sentence: str
    example_translation: Optional[str] = None


class FlashcardRead(ORMModel):
    id: int
    category: str
    word: str
    ipa: Optional[str] = None
    word_type: Optional[str] = None
    meaning: str
    collocations: Optional[str] = None
    paraphrase_pair: Optional[str] = None
    example_sentence: str
    example_translation: Optional[str] = None
    audio_word_url: Optional[str] = None
    audio_sentence_url: Optional[str] = None


class TranslateSentenceRequest(BaseModel):
    sentence: str = Field(..., min_length=1, max_length=1000)


class TranslateSentenceResponse(BaseModel):
    sentence: str
    translation: str


class CategoryStat(BaseModel):
    category: str
    total: int
    due: int
    mastered: int
    learning: int
    new_cards: int


class FlashcardSummary(BaseModel):
    total_cards: int
    mastered_cards: int
    due_cards: int
    review_due: int
    new_available: int
    new_cards: int
    learning_cards: int
    reviewed_today: int
    new_cards_per_day: int
    categories: Dict[str, int]
    category_stats: Optional[List[CategoryStat]] = None


class UserCardSRSRead(ORMModel):
    id: int
    card_id: int
    flashcard: FlashcardRead
    repetition_count: int
    ease_factor: float
    interval_days: int
    state: str
    next_review_at: datetime
    last_reviewed_at: Optional[datetime] = None


class SRSReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=4, description="1: Again, 2: Hard, 3: Good, 4: Easy")
    duration_ms: Optional[int] = Field(None, ge=0, le=3_600_000, description="Thời gian học viên dùng cho thẻ")


# --------------------------------------------------------------------------- error logs
class ErrorLogCreate(BaseModel):
    # docs/index.html (legacy UI) posts quiz errors as error_code / remedy_rule, which used to fail with 422.
    model_config = ConfigDict(populate_by_name=True)

    test_id: Optional[str] = Field("Practice", max_length=50)
    part: str
    question_no: Optional[int] = Field(None, ge=1, le=200)
    question_id: Optional[int] = None
    error_type: ErrorType = Field(validation_alias=AliasChoices("error_type", "error_code"))
    user_choice: Optional[str] = None
    correct_choice: Optional[str] = None
    question_content: Optional[str] = Field(None, max_length=4000)
    image_url: Optional[str] = Field(None, max_length=255)
    root_cause: str = Field(..., min_length=1, max_length=2000)
    key_rule_or_paraphrase: Optional[str] = Field(
        None, max_length=2000, validation_alias=AliasChoices("key_rule_or_paraphrase", "remedy_rule")
    )
    topic: Optional[str] = Field(None, max_length=150)

    @field_validator("error_type", mode="before")
    @classmethod
    def _upper_error_type(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("part", mode="before")
    @classmethod
    def _normalize_part(cls, value):
        part = normalize_part(value)
        if part is None:
            raise ValueError("Part phải từ 'Part 1' đến 'Part 7'")
        return part

    @field_validator("user_choice", "correct_choice", mode="before")
    @classmethod
    def _choices(cls, value):
        return _upper_choice(value)


class ErrorLogUpdate(BaseModel):
    error_type: Optional[ErrorType] = None
    root_cause: Optional[str] = Field(None, min_length=1, max_length=2000)
    key_rule_or_paraphrase: Optional[str] = Field(None, max_length=2000)
    status: Optional[ErrorStatus] = None

    @field_validator("error_type", mode="before")
    @classmethod
    def _upper_error_type(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class ErrorLogRead(ORMModel):
    id: int
    test_id: Optional[str] = None
    part: str
    question_no: Optional[int] = None
    question_id: Optional[int] = None
    error_type: str
    user_choice: Optional[str] = None
    correct_choice: Optional[str] = None
    question_content: Optional[str] = None
    image_url: Optional[str] = None
    root_cause: str
    key_rule_or_paraphrase: Optional[str] = None
    topic: Optional[str] = None
    lesson_number: Optional[int] = None
    source: Optional[str] = None
    status: str
    review_count: int
    review_stage: Optional[int] = None
    next_review_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime


# --------------------------------------------------------------------------- knowledge
class LessonStats(BaseModel):
    question_count: int
    answered: int
    correct: int
    accuracy: Optional[float] = None
    open_errors: int
    status: Literal["not_started", "weak", "improving", "strong"]
    mastery: Optional[float] = None
    confidence: Optional[float] = None
    attempts: int = 0
    avg_time_seconds: Optional[float] = None
    trend: Optional[float] = None


class KnowledgeLessonRead(BaseModel):
    id: int
    lesson_number: int
    title: str
    subtitle: Optional[str] = None
    syntax_formula: Optional[str] = None
    summary: Optional[str] = None
    content_html: str
    is_unlocked: bool
    has_full_content: bool
    stats: LessonStats


class LessonNoteRead(ORMModel):
    id: int
    lesson_number: int
    content: str
    source: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class LessonNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class LessonProgressRead(BaseModel):
    lesson_number: int
    time_spent_seconds: int = 0
    view_count: int = 0
    first_viewed_at: Optional[datetime] = None
    last_viewed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LessonProgressUpdate(BaseModel):
    event: Literal["view", "heartbeat", "complete", "uncomplete"] = "heartbeat"
    seconds: int = Field(0, ge=0, le=600)


class KnowledgeLessonDetail(KnowledgeLessonRead):
    content_md: Optional[str] = None
    questions: List[QuestionRead] = []
    notes: List[LessonNoteRead] = []
    progress: Optional[LessonProgressRead] = None


class ParaphrasePairRead(ORMModel):
    id: int
    word_in_text: str
    word_in_answer: str
    meaning: Optional[str] = None
    context_example: Optional[str] = None
    part_target: Optional[str] = None
    frequency: Optional[str] = None


# --------------------------------------------------------------------------- AI mentor
class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    question_id: Optional[Union[int, str]] = Field(None, description="TestQuestion.id hoặc 'ETS2024_01_108'")
    image_base64: Optional[str] = Field(None, max_length=8_000_000)
    user_id: int = Field(1, ge=1)
    page_context: Optional[str] = Field(None, max_length=200)
    include_history: bool = True


class AIChatResponse(BaseModel):
    reply: str
    actions_taken: List[Dict[str, Any]] = []
    suggested_questions: List[str] = []
    provider: str = "offline"
    model: Optional[str] = None


class VoiceCoachFeedback(BaseModel):
    grammar_score: int = Field(80, ge=0, le=100)
    fluency_score: int = Field(80, ge=0, le=100)
    grammar_notes: Optional[str] = None
    better_expression: Optional[str] = None
    paraphrase_suggestion: Optional[str] = None
    pronunciation_tips: Optional[str] = None
    acoustic_notes: Optional[str] = None


class VoiceCoachStartRequest(BaseModel):
    scenario: str = Field("business_office", description="business_office | tech_interview | customer_service | free_conversation")
    accent: Optional[str] = Field("en-US-JennyNeural", description="TTS voice accent")


class VoiceCoachStartResponse(BaseModel):
    scenario: str
    scenario_title: str
    ai_opening_statement: str
    audio_url: str


class VoiceCoachTurnRequest(BaseModel):
    scenario: str = Field("business_office")
    user_transcript: Optional[str] = Field(None, max_length=2000)
    audio_base64: Optional[str] = Field(None, max_length=15_000_000)
    history: List[Dict[str, str]] = Field(default_factory=list)
    accent: Optional[str] = Field("en-US-JennyNeural")


class VoiceCoachTurnResponse(BaseModel):
    user_transcript: Optional[str] = None
    spoken_reply: str
    audio_url: str
    feedback: VoiceCoachFeedback
    provider: str
    model: Optional[str] = None


class VocabPronounceFeedback(BaseModel):
    vowels: str
    consonants: str
    stress: str
    tips: str


class VocabPronounceRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    expected_ipa: Optional[str] = Field(None, max_length=100)
    audio_base64: str = Field(..., min_length=10, max_length=15_000_000)
    user_transcript: Optional[str] = Field(None, max_length=500)


class VocabPronounceResponse(BaseModel):
    word: str
    score: int = Field(..., ge=0, le=100)
    recognized_text: str
    recognized_ipa: str
    expected_ipa: str
    is_accurate: bool
    feedback: VocabPronounceFeedback
    provider: str
    model: Optional[str] = None
    is_guidance_fallback: bool = False


class AIMessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    actions: List[Dict[str, Any]] = []


class AIStatus(BaseModel):
    provider: str
    model: Optional[str] = None
    vision: bool
    audio: bool = False
    audio_model: Optional[str] = None
    offline: bool
    configured_providers: List[str]
    fallback_providers: List[str] = []


class AIActionRead(BaseModel):
    id: int
    tool: str
    source: Optional[str] = None
    summary: Optional[str] = None
    status: str
    undoable: bool
    created_at: datetime
    undone_at: Optional[datetime] = None


class AIToolExecuteRequest(BaseModel):
    tool: str = Field(..., min_length=2, max_length=60)
    args: Dict[str, Any] = Field(default_factory=dict)
    source: Literal["user", "coach"] = "coach"


class AIToolInfo(BaseModel):
    name: str
    description: str
    writes: bool
    category: str


# --------------------------------------------------------------------------- learner (personalization)
MemoryCategory = Literal["goal", "preference", "struggle", "strength", "context", "other"]


class LearnerMemoryRead(ORMModel):
    id: int
    category: str
    content: str
    source: str
    pinned: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class LearnerMemoryCreate(BaseModel):
    content: str = Field(..., min_length=2, max_length=500)
    category: MemoryCategory = "other"
    pinned: bool = False


class LearnerMemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=2, max_length=500)
    category: Optional[MemoryCategory] = None
    pinned: Optional[bool] = None


class ActivityPing(BaseModel):
    kind: Literal["lesson", "listening", "reading", "srs", "practice", "other"]
    seconds: int = Field(..., ge=1, le=600)
    ref: Optional[str] = Field(None, max_length=50)


class Suggestion(BaseModel):
    id: str
    title: str
    detail: str
    priority: int
    kind: Literal["tool", "mentor", "link"]
    cta: str
    tool: Optional[str] = None
    args: Dict[str, Any] = {}
    href: Optional[str] = None
    prompt: Optional[str] = None


# --------------------------------------------------------------------------- plan
PlanStatus = Literal["pending", "done", "skipped"]


class PlanItemRead(BaseModel):
    id: int
    date: date
    kind: str
    tag: str
    title: str
    detail: Optional[str] = None
    reason: Optional[str] = None
    lesson_number: Optional[int] = None
    part: Optional[str] = None
    target_count: Optional[int] = None
    progress: Optional[int] = None
    estimated_minutes: int = 0
    priority: int = 0
    status: str
    auto: bool
    source: str
    href: str
    ref: Optional[str] = None


class PlanItemCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=300)
    plan_date: date
    estimated_minutes: int = Field(15, ge=1, le=240)
    lesson_number: Optional[int] = Field(None, ge=1, le=12)
    detail: Optional[str] = Field(None, max_length=1000)


class PlanItemUpdate(BaseModel):
    status: Optional[PlanStatus] = None
    plan_date: Optional[date] = None
    title: Optional[str] = Field(None, min_length=2, max_length=300)


# --------------------------------------------------------------------------- reminders
class StudyReminderRead(ORMModel):
    id: int
    reminder_type: str
    scheduled_time: str
    message: str
    is_active: bool
    last_triggered_at: Optional[datetime] = None


class StudyReminderCreate(BaseModel):
    reminder_type: Literal["daily_study", "review_error_log", "srs_due", "weekly_report"] = "daily_study"
    scheduled_time: str = Field(..., pattern=HHMM_PATTERN)
    message: str = Field(..., min_length=1, max_length=500)


class StudyReminderUpdate(BaseModel):
    scheduled_time: Optional[str] = Field(None, pattern=HHMM_PATTERN)
    message: Optional[str] = Field(None, min_length=1, max_length=500)
    is_active: Optional[bool] = None


# --------------------------------------------------------------------------- listening / dictation
class DictationDiffToken(BaseModel):
    word: str
    status: Literal["correct", "missing", "extra", "misspelled"]
    learner_word: Optional[str] = ""


class DictationCheckRequest(BaseModel):
    question_id: int
    learner_text: str = Field(..., max_length=2000)
    target_transcript: Optional[str] = Field(None, max_length=2000)
    time_spent_seconds: Optional[int] = Field(0, ge=0, le=7200)


class DictationCheckResponse(BaseModel):
    accuracy: float
    is_perfect: bool
    correct_words: int
    total_words: int
    tokens: List[DictationDiffToken]
    target_transcript: str
    learner_text: str
    phonetic_cues: List[str]


class ListeningExercise(BaseModel):
    id: int
    test_id: str
    part: str
    question_no: int
    sentence: str
    target_transcript: str
    explanation: Optional[str] = None
    distractor_analysis: Optional[str] = None
    paraphrase_pair: Optional[str] = None
    accent: str
    voice: str
    difficulty: str
    phonetic_cues: List[str]
    choice_a: Optional[str] = None
    choice_b: Optional[str] = None
    choice_c: Optional[str] = None
    choice_d: Optional[str] = None
    correct_choice: Optional[str] = None


class ListeningTrackRequest(BaseModel):
    seconds: int = Field(..., ge=1, le=7200)


class ShadowingWordFeedback(BaseModel):
    word: str
    status: Literal["perfect", "good", "needs_work", "missed"]
    ipa: Optional[str] = None
    note: Optional[str] = None


class ShadowingEvaluateRequest(BaseModel):
    exercise_id: Optional[int] = None
    target_sentence: str = Field(..., max_length=2000)
    audio_base64: Optional[str] = None
    user_transcript: Optional[str] = Field(None, max_length=2000)
    phonetic_cues: Optional[List[str]] = None
    accent: Optional[str] = "US"


class ShadowingEvaluateResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    accuracy_score: int = Field(..., ge=0, le=100)
    fluency_score: int = Field(..., ge=0, le=100)
    recognized_transcript: str
    is_passing: bool
    verdict: str
    words: List[ShadowingWordFeedback]
    connected_speech_feedback: Optional[str] = None
    coaching_tips: List[str]
    provider: str
    model: str
    is_guidance_fallback: Optional[bool] = False
    analysis_mode: Optional[str] = "text_stt"


