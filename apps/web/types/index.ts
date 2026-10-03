// Types mirror server/schemas/__init__.py — keep both sides in sync.

export type ErrorType = "VOCAB" | "GRAMMAR" | "PHONETICS" | "TRAP" | "TIME";
export type ErrorStatus = "unresolved" | "reviewed" | "mastered";
export type LessonStatus = "not_started" | "weak" | "improving" | "strong";

export interface UserProfile {
  id: number;
  username: string;
  email?: string | null;
  display_name: string | null;
  headline: string | null;
  role?: string | null;
  avatar_url?: string | null;
  target_score: number;
  daily_goal_minutes: number;
  target_cefr: string | null;
  created_at: string;
  exam_date: string | null;
  days_to_exam: number | null;
  baseline_listening: number | null;
  baseline_reading: number | null;
  study_days: number[];
  new_cards_per_day: number | null;
  effective_new_cards_per_day: number;
  explanation_style: ExplanationStyle;
  focus_parts: string[];
  learning_goal_note: string | null;
  auto_adjust: boolean;
  onboarded: boolean;
  onboarded_at: string | null;
}

export interface AuthUser {
  id: number;
  username: string;
  email?: string | null;
  display_name?: string | null;
  headline?: string | null;
  target_score: number;
  target_cefr?: string | null;
  role?: string | null;
  avatar_url?: string | null;
  created_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export type ExplanationStyle = "concise" | "detailed" | "socratic";
export type PracticeMode = "practice" | "study" | "exam" | "review" | "smart";
export type SkillStatus = "not_started" | "weak" | "improving" | "strong";

export interface SkillStat {
  key: string;
  label: string;
  kind: "lesson" | "part" | "section";
  lesson_number: number | null;
  part: string | null;
  attempts: number;
  distinct_questions: number;
  latest_correct: number;
  accuracy: number | null;
  mastery: number;
  prior: number;
  confidence: number;
  trend: number | null;
  avg_time_seconds: number | null;
  target_seconds: number | null;
  last_attempt_at: string | null;
  open_errors: number;
  question_count: number;
  unseen_questions: number;
  status: SkillStatus;
}

export interface SectionPrediction {
  expected: number;
  low: number;
  high: number;
  expected_raw: number;
  basis: "data" | "baseline" | "prior";
  confidence: number;
  parts: Record<string, { accuracy: number; confidence: number; observed: boolean }>;
}

export interface ScorePrediction {
  listening: SectionPrediction;
  reading: SectionPrediction;
  total: { expected: number; low: number; high: number; cefr: string };
  confidence: number;
  confidence_level?: "low" | "medium" | "high";
  questions_needed_to_narrow?: number;
  target_score: number;
  target_gap: number;
}

export interface FocusLesson {
  lesson_number: number;
  title: string;
  mastery: number;
  status: SkillStatus;
  attempts: number;
  open_errors: number;
  question_count: number;
  reason: string;
}

export interface LearnerInsights {
  lessons: SkillStat[];
  parts: SkillStat[];
  sections: Record<string, SkillStat>;
  prediction: ScorePrediction;
  pace: { part: string; avg_seconds: number; target_seconds: number; slow: boolean }[];
  srs_retention: { reviews: number; retained: number; rate: number | null; days: number };
  leech_cards: { card_id: number; word: string; meaning: string; lapses: number; state: string | null }[];
  study_minutes: { date: string; minutes: number; goal_minutes: number; by_kind: Record<string, number> }[];
  focus: FocusLesson[];
  total_attempts: number;
  priors: Record<string, number>;
}

export interface PlanItem {
  id: number;
  date: string;
  kind: "srs" | "error_review" | "lesson" | "practice" | "smart" | "mock" | "listening" | "ai_generate" | "custom";
  tag: string;
  title: string;
  detail: string | null;
  reason: string | null;
  lesson_number: number | null;
  part: string | null;
  target_count: number | null;
  progress: number | null;
  estimated_minutes: number;
  priority: number;
  status: "pending" | "done" | "skipped";
  auto: boolean;
  source: "planner" | "user" | "ai_mentor" | "coach";
  href: string;
  ref: string | null;
}

export interface PlanDay {
  date: string;
  weekday: string;
  is_today: boolean;
  is_study_day: boolean;
  planned_minutes: number;
  done_minutes: number;
  studied_minutes: number;
  items: PlanItem[];
}

export interface PlanWeek {
  start: string;
  end: string;
  generated_on: string | null;
  settings: {
    daily_minutes: number;
    planned_daily_minutes: number;
    auto_adjust: boolean;
    adjustments: string[];
    study_days: number[];
    new_cards_per_day: number;
    exam_date: string | null;
    days_to_exam: number | null;
    focus_parts: string[];
  };
  focus: FocusLesson[];
  days: PlanDay[];
  history: {
    days: number;
    planned_items: number;
    done_items: number;
    completion_rate: number | null;
    studied_minutes: number;
    goal_minutes: number;
    behind: boolean;
  };
}

export interface Suggestion {
  id: string;
  title: string;
  detail: string;
  priority: number;
  kind: "tool" | "mentor" | "link";
  cta: string;
  tool: string | null;
  args: Record<string, unknown>;
  href: string | null;
  prompt: string | null;
}

export interface LearnerMemory {
  id: number;
  category: "goal" | "preference" | "struggle" | "strength" | "context" | "other";
  content: string;
  source: string;
  pinned: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface AIActionLog {
  id: number;
  tool: string;
  source: string | null;
  summary: string | null;
  status: "applied" | "undone";
  undoable: boolean;
  created_at: string;
  undone_at: string | null;
}

export interface AIToolInfo {
  name: string;
  description: string;
  writes: boolean;
  category: string;
}

export interface ToolExecuteResult {
  tool: string;
  status: "success" | "exists" | "noop" | "error" | "ignored";
  message: string;
  writes: boolean;
  data?: Record<string, unknown>;
  action_id?: number;
  undoable?: boolean;
}

export interface LessonNote {
  id: number;
  lesson_number: number;
  content: string;
  source: string;
  created_at: string;
  updated_at: string | null;
}

export interface LessonProgress {
  lesson_number: number;
  time_spent_seconds: number;
  view_count: number;
  first_viewed_at: string | null;
  last_viewed_at: string | null;
  completed_at: string | null;
}

export interface PracticeQuestion extends TestQuestionItem {
  reason?: string | null;
  error_log_id?: number | null;
  review_stage?: number | null;
  difficulty?: "easy" | "medium" | "hard" | null;
}

export interface FlashcardItem {
  id: number;
  category: string;
  word: string;
  ipa?: string | null;
  word_type?: string | null;
  meaning: string;
  collocations?: string | null;
  paraphrase_pair?: string | null;
  example_sentence: string;
  example_translation?: string | null;
  audio_word_url?: string | null;
  audio_sentence_url?: string | null;
}

export interface CategoryStat {
  category: string;
  total: number;
  due: number;
  mastered: number;
  learning: number;
  new_cards: number;
}

export interface FlashcardSummary {
  total_cards: number;
  mastered_cards: number;
  due_cards: number;
  review_due: number;
  new_available: number;
  new_cards: number;
  learning_cards: number;
  reviewed_today: number;
  new_cards_per_day: number;
  categories: Record<string, number>;
  category_stats?: CategoryStat[];
}

export interface SrsCard {
  id: number;
  card_id: number;
  flashcard: FlashcardItem;
  repetition_count: number;
  ease_factor: number;
  interval_days: number;
  state: "new" | "learning" | "review" | "mastered";
  next_review_at: string;
  last_reviewed_at?: string | null;
}

export interface TestQuestionItem {
  id: number;
  test_id: string;
  part: string;
  question_no: number;
  sentence: string;
  choice_a: string;
  choice_b: string;
  choice_c: string;
  choice_d?: string | null;
  correct_choice: string;
  explanation?: string | null;
  distractor_analysis?: string | null;
  paraphrase_pair?: string | null;
  trap_tag?: string | null;
  error_type: ErrorType;
  lesson_number?: number | null;
  source?: string | null;
  image_url?: string | null;
}

export interface MockTestItem {
  id: number;
  test_id: string;
  name: string;
  year?: number | null;
  publisher?: string | null;
  total_questions?: number | null;
  available_questions: number;
  category?: "mock" | "drill" | string | null;
  parts: Record<string, number>;
}

export interface LearningGap {
  id: number;
  topic: string;
  error_count: number;
  severity: "low" | "medium" | "high" | "critical";
  lesson_number?: number | null;
  lesson_title?: string | null;
  ai_recommendation?: string | null;
}

export interface QuestionResult {
  question_id: number;
  question_no: number;
  part: string;
  user_choice: string | null;
  correct_choice: string;
  is_correct: boolean;
  error_type: ErrorType;
  trap_tag?: string | null;
  lesson_number?: number | null;
  error_log_id?: number | null;
  test_id?: string | null;
  time_ms?: number | null;
  review_outcome?: "advanced" | "mastered" | "reset" | "early" | null;
}

export interface QuizSubmitResult {
  submission_id: number;
  test_id: string;
  part?: string | null;
  lesson_number?: number | null;
  correct_count: number;
  total_questions: number;
  unanswered: number;
  accuracy: number;
  scaled_listening?: number | null;
  scaled_reading?: number | null;
  errors_logged: number;
  mode: PracticeMode;
  reviews_advanced: number;
  errors_mastered: number;
  avg_time_seconds?: number | null;
  time_spent_seconds: number;
  results: QuestionResult[];
  learning_gaps: LearningGap[];
}

export interface Submission {
  id: number;
  test_id: string;
  part?: string | null;
  mode?: PracticeMode | null;
  lesson_number?: number | null;
  correct_count?: number | null;
  total_questions?: number | null;
  accuracy?: number | null;
  scaled_listening?: number | null;
  scaled_reading?: number | null;
  total_scaled_score?: number | null;
  time_spent_seconds?: number | null;
  submitted_at: string;
}

export interface DayActivity {
  date: string;
  weekday: string;
  is_today: boolean;
  is_future: boolean;
  srs_reviews: number;
  questions_answered: number;
  errors_logged: number;
  tasks_completed: number;
  mentor_questions: number;
  minutes: number;
  total: number;
  active: boolean;
}

export interface TodayTask {
  key: string;
  title: string;
  tag: string;
  href: string;
  done: boolean;
  detail?: string | null;
  kind: PlanItem["kind"] | "milestone";
  status: "pending" | "done" | "skipped";
  auto: boolean;
  reason?: string | null;
  estimated_minutes?: number | null;
  progress?: number | null;
  target?: number | null;
  plan_item_id?: number | null;
  lesson_number?: number | null;
}

export interface LessonBrief {
  lesson_number: number;
  title: string;
  subtitle?: string | null;
  syntax_formula?: string | null;
  summary?: string | null;
  reason: string;
  question_count: number;
  accuracy?: number | null;
  mastery?: number | null;
  status: LessonStatus;
}

export interface DashboardStats {
  target_score: number;
  roadmap_percent: number;
  completed_tasks: number;
  total_tasks: number;
  srs_due_count: number;
  srs_mastered_count: number;
  total_flashcards: number;
  total_errors: number;
  rca_breakdown: Record<string, number>;
  top_learning_gaps: string[];
  display_name: string;
  headline?: string | null;
  target_cefr: string;
  daily_goal_minutes: number;
  current_week: number;
  total_weeks: number;
  current_phase: number;
  roadmap_title?: string | null;
  srs_review_due: number;
  srs_new_available: number;
  srs_reviewed_today: number;
  srs_learning_count: number;
  open_errors: number;
  learning_gaps: LearningGap[];
  streak_days: number;
  activity_week: DayActivity[];
  today_tasks: TodayTask[];
  recommended_lesson?: LessonBrief | null;
  latest_submission?: Submission | null;
  srs_new_cards_per_day: number;
  error_reviews_due: number;
  study_minutes_today: number;
  study_minutes_week: number;
  today_plan_minutes: number;
  predicted_score?: {
    total: number;
    low: number;
    high: number;
    listening: number;
    reading: number;
    confidence: number;
    confidence_level?: "low" | "medium" | "high";
    questions_needed_to_narrow?: number;
    basis_listening: string;
    basis_reading: string;
  } | null;
  onboarded: boolean;
  exam_date?: string | null;
  days_to_exam?: number | null;
  total_attempts: number;
}

export interface SprintTask {
  id: number;
  phase: number;
  week_number: number;
  category: string;
  title: string;
  is_completed: boolean;
  completed_at?: string | null;
  base_week?: number | null;
  source?: string | null;
  auto_met: boolean;
  evidence?: string | null;
}

export interface Roadmap {
  id: number;
  title: string;
  total_weeks: number;
  base_total_weeks?: number | null;
  exam_date?: string | null;
  current_week: number;
  current_phase: number;
  start_date: string;
  status: string;
  progress_percent: number;
  completed_tasks: number;
  total_tasks: number;
  tasks: SprintTask[];
}

export interface ErrorLogEntry {
  id: number;
  test_id?: string | null;
  part: string;
  question_no?: number | null;
  question_id?: number | null;
  error_type: ErrorType;
  user_choice?: string | null;
  correct_choice?: string | null;
  question_content?: string | null;
  image_url?: string | null;
  root_cause: string;
  key_rule_or_paraphrase?: string | null;
  topic?: string | null;
  lesson_number?: number | null;
  source?: "manual" | "mock_test" | "ai_mentor" | null;
  status: ErrorStatus;
  review_count: number;
  review_stage?: number | null;
  next_review_at?: string | null;
  last_reviewed_at?: string | null;
  created_at: string;
}

export interface LessonStats {
  question_count: number;
  answered: number;
  correct: number;
  accuracy?: number | null;
  open_errors: number;
  status: LessonStatus;
  mastery?: number | null;
  confidence?: number | null;
  attempts?: number;
  avg_time_seconds?: number | null;
  trend?: number | null;
}

export interface Lesson {
  id: number;
  lesson_number: number;
  title: string;
  subtitle?: string | null;
  syntax_formula?: string | null;
  summary?: string | null;
  content_html: string;
  is_unlocked: boolean;
  has_full_content: boolean;
  stats: LessonStats;
}

export interface LessonDetail extends Lesson {
  content_md?: string | null;
  questions: TestQuestionItem[];
  notes: LessonNote[];
  progress?: Partial<LessonProgress> | null;
}

export interface ScoreCalcResult {
  raw_listening: number;
  raw_reading: number;
  scaled_listening: number;
  scaled_reading: number;
  total_score: number;
  cefr_code: string;
  cefr_level: string;
  cefr_description: string;
  target_score: number;
  target_gap: number;
  suggested_gain_listening: number;
  suggested_gain_reading: number;
  recommendations: string[];
}

export interface AIAction {
  tool: string;
  status: "success" | "exists" | "noop" | "error" | "ignored";
  message: string;
  writes?: boolean;
  data?: Record<string, unknown>;
  action_id?: number;
  undoable?: boolean;
  /** Frontend-only: the change was undone afterwards */
  undone?: boolean;
}

export interface AIChatResponse {
  reply: string;
  actions_taken: AIAction[];
  suggested_questions: string[];
  provider: string;
  model?: string | null;
}

export interface AIHistoryMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  actions: AIAction[];
}

export interface AIStatus {
  provider: string;
  model?: string | null;
  vision: boolean;
  audio?: boolean;
  audio_model?: string | null;
  offline: boolean;
  configured_providers: string[];
  fallback_providers?: string[];
}

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  ai: AIStatus;
  telegram_configured: boolean;
  cached_audio_count: number;
}

export interface Voice {
  id: string;
  name: string;
  accent: string;
  gender: string;
  description: string;
}

export interface StudyReminder {
  id: number;
  reminder_type: "daily_study" | "review_error_log" | "srs_due" | "weekly_report";
  scheduled_time: string;
  message: string;
  is_active: boolean;
  last_triggered_at?: string | null;
}

export interface ParaphrasePair {
  id: number;
  word_in_text: string;
  word_in_answer: string;
  meaning: string | null;
  context_example: string | null;
  part_target: string | null;
  frequency: string | null;
}

export interface WeeklyMasteryChange {
  lesson_number: number;
  title: string;
  attempts: number;
  mastery_before: number;
  mastery_after: number;
  delta: number;
  first_time: boolean;
}

export interface WeeklyReport {
  start: string;
  end: string;
  new_learner: boolean;
  study: { minutes: number; goal_minutes: number; goal_rate: number | null; active_days: number; planned_days: number; by_kind: Record<string, number> };
  practice: { questions: number; correct: number; accuracy: number | null; previous_accuracy: number | null; accuracy_delta: number | null; avg_seconds: number | null };
  mastery_changes: WeeklyMasteryChange[];
  prediction: { total: number; previous_total: number; delta: number; confidence: number; target: number };
  errors: { new: number; mastered: number; open: number; reviews_next_week: number };
  vocab: { reviews: number; new_cards: number; retention: number | null };
  plan: { items: number; done: number; completion: number | null };
  next_focus: { lesson_number: number; title: string; reason: string }[];
  days_to_exam: number | null;
  highlights: string[];
  recommendations: string[];
  markdown: string;
}

// --------------------------------------------------------------------------- listening & dictation
export interface DictationDiffToken {
  word: string;
  status: "correct" | "misspelled" | "missing" | "extra";
  learner_word?: string | null;
}

export interface DictationCheckRequest {
  question_id: number;
  learner_text: string;
  target_transcript?: string | null;
  time_spent_seconds?: number;
}

export interface DictationCheckResponse {
  accuracy: number;
  is_perfect: boolean;
  correct_words: number;
  total_words: number;
  tokens: DictationDiffToken[];
  target_transcript: string;
  learner_text: string;
  phonetic_cues: string[];
}

export interface ListeningExercise {
  id: number;
  test_id: string;
  part: string;
  question_no: number | null;
  sentence: string;
  target_transcript: string;
  explanation: string | null;
  distractor_analysis: string | null;
  paraphrase_pair: string | null;
  accent: "US" | "UK" | "AU" | "CA" | string;
  voice: string;
  difficulty: "easy" | "medium" | "hard" | string;
  phonetic_cues: string[];
  choice_a: string | null;
  choice_b: string | null;
  choice_c: string | null;
  choice_d: string | null;
  correct_choice: string | null;
}

export interface VoiceCoachFeedback {
  grammar_score: number;
  fluency_score: number;
  grammar_notes?: string | null;
  better_expression?: string | null;
  paraphrase_suggestion?: string | null;
  pronunciation_tips?: string | null;
  acoustic_notes?: string | null;
}

export interface VoiceCoachStartResponse {
  scenario: string;
  scenario_title: string;
  ai_opening_statement: string;
  audio_url: string;
}

export interface VoiceCoachTurnResponse {
  user_transcript?: string;
  spoken_reply: string;
  audio_url: string;
  feedback: VoiceCoachFeedback;
  provider: string;
  model?: string | null;
}

export interface VoiceMessage {
  id: string;
  role: "ai" | "user";
  text: string;
  audioUrl?: string;
  feedback?: VoiceCoachFeedback;
  timestamp: string;
}

export interface VocabPronounceFeedback {
  vowels: string;
  consonants: string;
  stress: string;
  tips: string;
}

export interface VocabPronounceResponse {
  word: string;
  score: number;
  recognized_text: string;
  recognized_ipa: string;
  expected_ipa: string;
  is_accurate: boolean;
  feedback: VocabPronounceFeedback;
  provider: string;
  model?: string | null;
  is_guidance_fallback?: boolean;
}

export interface ShadowingWordFeedback {
  word: string;
  status: "perfect" | "good" | "needs_work" | "missed";
  ipa?: string | null;
  note?: string | null;
}

export interface ShadowingEvaluateRequest {
  exercise_id?: number | null;
  target_sentence: string;
  audio_base64?: string | null;
  user_transcript?: string | null;
  phonetic_cues?: string[] | null;
  accent?: string | null;
}

export interface ShadowingEvaluateResponse {
  overall_score: number;
  accuracy_score: number;
  fluency_score: number;
  recognized_transcript: string;
  is_passing: boolean;
  verdict: string;
  words: ShadowingWordFeedback[];
  connected_speech_feedback?: string | null;
  coaching_tips: string[];
  provider: string;
  model: string;
  is_guidance_fallback?: boolean;
  analysis_mode?: "audio_multimodal" | "text_stt" | "guidance" | string;
}



