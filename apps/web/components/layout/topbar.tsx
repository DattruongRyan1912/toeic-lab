"use client";

import Link from "next/link";
import { CalendarClock, Flame, Sparkles, Target } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useLearnerStore } from "@/lib/learner-store";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  return (parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Topbar() {
  const stats = useLearnerStore((state) => state.stats);
  const error = useLearnerStore((state) => state.error);
  const name = stats?.display_name ?? "…";

  return (
    <header className="z-20 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white/90 px-6 shadow-xs backdrop-blur-md transition-colors duration-200 dark:border-slate-800/80 dark:bg-[#0f172a]/90 dark:shadow-none">
      <div className="flex items-center gap-3">
        <Link href="/analytics" className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs dark:border-slate-700/60 dark:bg-slate-800/80">
          <Target className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" aria-hidden="true" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">Mục tiêu: {stats ? `${stats.target_score}+ TOEIC` : "…"}</span>
          {stats && <span className="hidden font-mono text-[10px] text-slate-500 sm:inline dark:text-slate-400">• {stats.target_cefr.split(" - ")[0]}</span>}
        </Link>
        {stats && (
          <span
            className="hidden items-center gap-1.5 rounded-full border border-orange-500/20 bg-orange-500/10 px-3 py-1 text-xs font-medium text-orange-600 sm:flex dark:text-orange-400"
            title="Số ngày liên tiếp có ít nhất 1 phút học thật (SRS, làm bài, đọc bài, listening, hỏi Mentor)"
          >
            <Flame className="h-3.5 w-3.5 fill-orange-500 text-orange-500 dark:fill-orange-400 dark:text-orange-400" aria-hidden="true" />
            {stats.streak_days > 0 ? `Chuỗi ${stats.streak_days} ngày học` : "Bắt đầu chuỗi học hôm nay"}
          </span>
        )}
        {stats && !stats.onboarded ? (
          <Link href="/onboarding" className="flex items-center gap-1.5 rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white hover:bg-blue-500">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" /> Cá nhân hoá lộ trình
          </Link>
        ) : stats ? (
          <Link
            href="/settings#personalization"
            className="hidden items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-700 md:flex dark:border-slate-700/60 dark:text-slate-300"
            title={stats.exam_date ? `Ngày thi ${stats.exam_date}` : "Đặt ngày thi để lộ trình tự co giãn"}
          >
            <CalendarClock className="h-3.5 w-3.5 text-purple-500" aria-hidden="true" />
            {stats.days_to_exam != null && stats.days_to_exam >= 0 ? `Còn ${stats.days_to_exam} ngày thi` : "Đặt ngày thi"}
          </Link>
        ) : null}
        {error && !stats && <span className="text-xs text-red-500">{error}</span>}
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggle />
        <Link href="/settings" className="flex items-center gap-3 border-l border-slate-200 pl-3 dark:border-slate-800" aria-label="Hồ sơ học viên">
          <div className="hidden text-right sm:block">
            <p className="text-xs leading-tight font-semibold text-slate-800 dark:text-slate-200">{name}</p>
            <p className="mt-0.5 font-mono text-[10px] leading-tight text-slate-500 dark:text-slate-400">
              {stats?.headline ?? (stats ? `Tuần ${stats.current_week}/${stats.total_weeks}` : "")}
            </p>
          </div>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-xs font-bold text-white shadow-inner ring-2 ring-blue-500/20">
            {stats ? initials(name) : "…"}
          </div>
        </Link>
      </div>
    </header>
  );
}
