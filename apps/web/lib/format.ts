import type { ErrorStatus, ErrorType, LessonStatus } from "@/types";

export const ERROR_TYPES: { key: ErrorType; label: string; color: string; bar: string }[] = [
  { key: "VOCAB", label: "Thiếu từ vựng & Collocation", color: "text-blue-600 dark:text-blue-400", bar: "bg-blue-500" },
  { key: "GRAMMAR", label: "Sai ngữ pháp & cấu trúc câu", color: "text-purple-600 dark:text-purple-400", bar: "bg-purple-500" },
  { key: "PHONETICS", label: "Biến âm & nối âm Listening", color: "text-amber-600 dark:text-amber-400", bar: "bg-amber-500" },
  { key: "TRAP", label: "Mắc bẫy đề thi ETS", color: "text-red-600 dark:text-red-400", bar: "bg-red-500" },
  { key: "TIME", label: "Hết giờ / áp lực thời gian", color: "text-emerald-600 dark:text-emerald-400", bar: "bg-emerald-500" },
];

export const STATUS_LABELS: Record<ErrorStatus, string> = {
  unresolved: "Chưa khắc phục",
  reviewed: "Đã xem lại",
  mastered: "Đã nắm chắc",
};

export const STATUS_STYLES: Record<ErrorStatus, string> = {
  unresolved: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30",
  reviewed: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/30",
  mastered: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30",
};

export const LESSON_STATUS: Record<LessonStatus, { label: string; style: string }> = {
  not_started: { label: "Chưa luyện", style: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700/40 dark:text-slate-300 dark:border-slate-600/60" },
  weak: { label: "Cần củng cố", style: "bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-500/30" },
  improving: { label: "Đang tiến bộ", style: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30" },
  strong: { label: "Vững", style: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30" },
};

export const SOURCE_LABELS: Record<string, string> = {
  manual: "Tự nhập",
  mock_test: "Thi thử",
  ai_mentor: "AI Mentor",
};

export function percent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDate(value: string | null | undefined, withTime = false): string {
  if (!value) return "—";
  // Backend timestamps are naive UTC ("2026-10-01T02:00:00"); dates are plain "2026-10-01".
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("vi-VN", withTime ? { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" } : { day: "2-digit", month: "2-digit" });
}

export function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(safe / 60);
  const rest = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

export function lessonHref(lessonNumber: number | null | undefined): string {
  return lessonNumber ? `/lessons?lesson=${lessonNumber}` : "/lessons";
}

/** Lesson numbers referenced in free text, e.g. "Bài 02 (...) & Bài 03 (...)". Mirrors server/services/curriculum.py. */
export function lessonNumbersIn(text: string): number[] {
  return Array.from(text.matchAll(/Bài\s*0?(\d{1,2})/gi))
    .map((match) => Number(match[1]))
    .filter((value) => value >= 1 && value <= 12);
}

export function ipa(value: string | null | undefined): string | null {
  if (!value) return null;
  return `/${value.replace(/^[\s/[]+|[\s/\]]+$/g, "")}/`;
}
