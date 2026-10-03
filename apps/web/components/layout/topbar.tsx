"use client";

import Link from "next/link";
import { CalendarClock, Flame, LogIn, LogOut, Menu, Sparkles, Target } from "lucide-react";
import React, { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useLearnerStore } from "@/lib/learner-store";
import { useAuthStore } from "@/lib/auth-store";
import { AuthModal } from "@/components/auth/auth-modal";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  return (parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Topbar() {
  const stats = useLearnerStore((state) => state.stats);
  const error = useLearnerStore((state) => state.error);
  const mobileNavOpen = useLearnerStore((state) => state.mobileNavOpen);
  const setMobileNavOpen = useLearnerStore((state) => state.setMobileNavOpen);

  const authUser = useAuthStore((state) => state.user);
  const initAuth = useAuthStore((state) => state.initAuth);
  const openLogin = useAuthStore((state) => state.openLogin);
  const openRegister = useAuthStore((state) => state.openRegister);
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    void initAuth();
  }, [initAuth]);

  const name = authUser?.display_name || stats?.display_name || "…";

  return (
    <>
    <header className="z-20 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white/90 px-3 sm:px-6 shadow-xs backdrop-blur-md transition-colors duration-200 dark:border-slate-800/80 dark:bg-[#0f172a]/90 dark:shadow-none">
      <div className="flex min-w-0 items-center gap-1.5 sm:gap-3">
        <button
          type="button"
          onClick={() => setMobileNavOpen(!mobileNavOpen)}
          className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 md:hidden dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label="Mở menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Link
          href="/analytics"
          className="flex shrink-0 items-center gap-1.5 sm:gap-2 rounded-full border border-slate-200 bg-slate-100 px-2 sm:px-2.5 py-1 text-xs dark:border-slate-700/60 dark:bg-slate-800/80"
          title="Mục tiêu điểm TOEIC"
        >
          <Target className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 shrink-0" aria-hidden="true" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            <span className="hidden sm:inline">Mục tiêu: </span>{stats ? `${stats.target_score}+` : "…"}
          </span>
          {stats && <span className="hidden font-mono text-[10px] text-slate-500 md:inline dark:text-slate-400">• {stats.target_cefr.split(" - ")[0]}</span>}
        </Link>
        {stats && (
          <span
            className="hidden items-center gap-1.5 rounded-full border border-orange-500/20 bg-orange-500/10 px-3 py-1 text-xs font-medium text-orange-600 sm:flex dark:text-orange-400 shrink-0"
            title="Số ngày liên tiếp có ít nhất 1 phút học thật (SRS, làm bài, đọc bài, listening, hỏi Mentor)"
          >
            <Flame className="h-3.5 w-3.5 fill-orange-500 text-orange-500 dark:fill-orange-400 dark:text-orange-400" aria-hidden="true" />
            {stats.streak_days > 0 ? `Chuỗi ${stats.streak_days} ngày học` : "Bắt đầu chuỗi học hôm nay"}
          </span>
        )}
        {stats && !stats.onboarded ? (
          <Link href="/onboarding" className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-blue-600 px-2.5 sm:px-3 py-1 text-xs font-semibold text-white hover:bg-blue-500 shrink-0">
            <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="hidden md:inline">Cá nhân hoá lộ trình</span>
            <span className="md:hidden">Cá nhân hoá</span>
          </Link>
        ) : stats ? (
          <Link
            href="/settings#personalization"
            className="hidden items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-700 md:flex dark:border-slate-700/60 dark:text-slate-300 shrink-0"
            title={stats.exam_date ? `Ngày thi ${stats.exam_date}` : "Đặt ngày thi để lộ trình tự co giãn"}
          >
            <CalendarClock className="h-3.5 w-3.5 text-purple-500" aria-hidden="true" />
            {stats.days_to_exam != null && stats.days_to_exam >= 0 ? `Còn ${stats.days_to_exam} ngày thi` : "Đặt ngày thi"}
          </Link>
        ) : null}
        {error && !stats && <span className="text-xs text-red-500 truncate">{error}</span>}
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <ThemeToggle />
        {authUser ? (
          <div className="flex shrink-0 items-center gap-2 border-l border-slate-200 pl-2.5 sm:pl-3 dark:border-slate-800">
            <Link href="/settings" className="flex items-center gap-2.5 text-right hover:opacity-85 transition-opacity" aria-label="Hồ sơ học viên">
              <div className="hidden text-right sm:block">
                <p className="text-xs leading-tight font-semibold text-slate-800 dark:text-slate-200">
                  {authUser.display_name || authUser.username}
                </p>
                <p className="mt-0.5 font-mono text-[10px] leading-tight text-slate-500 dark:text-slate-400">
                  {authUser.email || authUser.username}
                </p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-xs font-bold text-white shadow-inner ring-2 ring-blue-500/20 shrink-0">
                {initials(name)}
              </div>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void logout()}
              className="h-8 w-8 p-0 text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 cursor-pointer shrink-0"
              title="Đăng xuất"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="flex shrink-0 items-center gap-1.5 border-l border-slate-200 pl-2 sm:pl-3 dark:border-slate-800">
            <Button
              variant="outline"
              size="sm"
              onClick={openLogin}
              className="h-8 px-2 sm:px-2.5 text-xs font-medium cursor-pointer shrink-0"
            >
              <LogIn className="hidden sm:inline h-3.5 w-3.5 mr-1 text-slate-600 dark:text-slate-300" />
              Đăng nhập
            </Button>
            <Button
              size="sm"
              onClick={openRegister}
              className="h-8 px-2.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white cursor-pointer shrink-0 shadow-xs"
            >
              Đăng ký
            </Button>
          </div>
        )}
      </div>
    </header>
    <AuthModal />
    </>
  );
}
