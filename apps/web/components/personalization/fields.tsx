"use client";

import { cn } from "@/lib/utils";
import type { ExplanationStyle } from "@/types";

/** Mon=0 … Sun=6, same as the API (`study_days`). */
export const WEEKDAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
export const PARTS = ["Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6", "Part 7"];
export const STYLES: { value: ExplanationStyle; label: string; hint: string }[] = [
  { value: "concise", label: "Ngắn gọn", hint: "Đáp án + quy tắc cốt lõi, đọc trong 30 giây" },
  { value: "detailed", label: "Chi tiết", hint: "Phân tích 3 chiều đầy đủ, bảng paraphrase" },
  { value: "socratic", label: "Gợi mở", hint: "AI hỏi dẫn dắt để bạn tự tìm ra đáp án" },
];

export function Chip({ active, onClick, children, label }: { active: boolean; onClick: () => void; children: React.ReactNode; label?: string }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={label}
      onClick={onClick}
      className={cn(
        "cursor-pointer rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
        active ? "border-blue-500 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300",
      )}
    >
      {children}
    </button>
  );
}

export function StylePicker({ value, onChange }: { value: ExplanationStyle; onChange: (value: ExplanationStyle) => void }) {
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      {STYLES.map((style) => (
        <button
          key={style.value}
          type="button"
          aria-pressed={value === style.value}
          onClick={() => onChange(style.value)}
          className={cn(
            "cursor-pointer rounded-xl border p-3 text-left transition",
            value === style.value ? "border-blue-500 bg-blue-50 dark:bg-blue-600/15" : "border-slate-200 dark:border-slate-700",
          )}
        >
          <span className="block text-sm font-bold text-slate-900 dark:text-white">{style.label}</span>
          <span className="text-[11px] text-slate-500 dark:text-slate-400">{style.hint}</span>
        </button>
      ))}
    </div>
  );
}

/** Toggle a value in a list; study days stay sorted. */
export function toggled<T extends number | string>(list: T[], value: T): T[] {
  const next = list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  return typeof value === "number" ? ([...next] as number[]).sort((a, b) => a - b) as T[] : next;
}

/** Today's local date as YYYY-MM-DD (for date inputs). */
export function localToday(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
