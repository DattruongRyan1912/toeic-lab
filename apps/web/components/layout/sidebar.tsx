"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertCircle,
  Bot,
  Calculator,
  Calendar,
  CheckSquare,
  GraduationCap,
  Headphones,
  Layers,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { BrandLogo } from "@/components/brand/logo";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { PROVIDER_LABELS, useLearnerStore } from "@/lib/learner-store";
import { cn } from "@/lib/utils";
import type { AIStatus, DashboardStats, HealthStatus } from "@/types";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string | null;
  alert?: boolean;
}

export function useBackendHealth() {
  const [health, setHealth] = useState<{ ok: boolean; data: HealthStatus | null } | null>(null);
  useEffect(() => {
    let cancelled = false;
    const check = () =>
      api<HealthStatus>("/health").then(
        (data) => !cancelled && setHealth({ ok: data.status === "healthy", data }),
        () => !cancelled && setHealth({ ok: false, data: null }),
      );
    void check();
    const timer = window.setInterval(check, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);
  return health;
}

export function getSidebarNav(stats: DashboardStats | null, aiStatus: AIStatus | null, isAdmin = false): { studyNav: NavItem[]; toolsNav: NavItem[] } {
  return {
    studyNav: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Sổ Tay Từ Vựng", href: "/vocab", icon: Layers, badge: stats ? (stats.srs_due_count ? `${stats.srs_due_count} cần ôn` : "Xong ✓") : null, alert: Boolean(stats?.srs_review_due) },
      { label: "Luyện Nghe (Audio)", href: "/listening", icon: Headphones, badge: "Dictation" },
      { label: "Luyện Đề Thi Thử", href: "/mock-tests", icon: CheckSquare, badge: stats?.latest_submission?.accuracy != null ? `${Math.round(stats.latest_submission.accuracy * 100)}%` : "Part 5" },
      { label: "12 Chuyên Đề Cú Pháp", href: "/lessons", icon: GraduationCap, badge: stats?.recommended_lesson ? `Bài ${String(stats.recommended_lesson.lesson_number).padStart(2, "0")}` : null },
      { label: "Sổ Tay Lỗi Sai (RCA)", href: "/error-log", icon: AlertCircle, badge: stats?.open_errors ? `${stats.open_errors} mở` : null, alert: Boolean(stats?.open_errors) },
    ],
    toolsNav: [
      { label: "Phân Tích & Quy Đổi Điểm", href: "/analytics", icon: Calculator },
      { label: `Lộ Trình ${stats?.total_weeks ?? 24} Tuần`, href: "/roadmaps", icon: Calendar, badge: stats ? `Tuần ${stats.current_week}` : null },
      { label: "AI Mentor Copilot", href: "/mentor", icon: Bot, badge: aiStatus ? PROVIDER_LABELS[aiStatus.provider] ?? aiStatus.provider : null },
      { label: "Cài Đặt & Hồ Sơ", href: "/settings", icon: Settings },
      ...(isAdmin ? [{ label: "Quản Trị Hệ Thống", href: "/admin", icon: ShieldCheck, badge: "Admin" }] : []),
    ],
  };
}

export function NavSection({ title, items, pathname, onItemClick }: { title: string; items: NavItem[]; pathname: string; onItemClick?: () => void }) {
  return (
    <div className="space-y-1">
      <p className="mb-2 px-3 text-[11px] font-semibold tracking-wider text-slate-400 uppercase dark:text-slate-500">{title}</p>
      {items.map((item) => {
        const Icon = item.icon;
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onItemClick}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-all",
              active
                ? "border border-blue-200 bg-blue-50 font-semibold text-blue-600 shadow-xs dark:border-blue-500/30 dark:bg-blue-600/20 dark:text-blue-300"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/50 dark:hover:text-slate-200",
            )}
          >
            <span className="flex items-center gap-2.5">
              <Icon className={cn("h-4 w-4", active ? "text-blue-600 dark:text-blue-400" : "text-slate-400 dark:text-slate-500")} aria-hidden="true" />
              <span>{item.label}</span>
            </span>
            {item.badge && (
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 font-mono text-[9px]",
                  item.alert
                    ? "bg-red-100 font-bold text-red-700 dark:bg-red-500/20 dark:text-red-300"
                    : active
                      ? "bg-blue-100 font-bold text-blue-700 dark:bg-blue-500/20 dark:text-blue-300"
                      : "border border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700/50 dark:bg-slate-800 dark:text-slate-400",
                )}
              >
                {item.badge}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const stats = useLearnerStore((state) => state.stats);
  const aiStatus = useLearnerStore((state) => state.aiStatus);
  const isAdmin = useAuthStore((state) => state.user?.role === "admin");
  const health = useBackendHealth();

  const { studyNav, toolsNav } = getSidebarNav(stats, aiStatus, isAdmin);

  const online = health?.ok ?? false;
  return (
    <aside className="hidden md:flex h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white transition-colors duration-200 select-none dark:border-slate-800/80 dark:bg-[#0d162a]">
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5 dark:border-slate-800/80">
        <Link href="/" className="transition-opacity hover:opacity-95" aria-label="TOEIC Master Home">
          <BrandLogo size={34} subtitle="SELF-STUDY LAB" />
        </Link>
        <span className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500 dark:border-slate-700/60 dark:bg-slate-800/70 dark:text-slate-400">
          v{health?.data?.version ?? "2"}
        </span>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Điều hướng chính">
        <NavSection title="Học Tập & Luyện Đề" items={studyNav} pathname={pathname} />
        <div className="border-t border-slate-200 pt-3 dark:border-slate-800/70">
          <NavSection title="Công Cụ & Lộ Trình" items={toolsNav} pathname={pathname} />
        </div>
      </nav>

      <div className="border-t border-slate-200 bg-slate-50 p-3 dark:border-slate-800/80 dark:bg-[#0a1020]">
        <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-2 text-xs dark:border-slate-700/50 dark:bg-slate-800/50" role="status">
          <span className="flex items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full", health === null ? "bg-slate-400" : online ? "animate-pulse bg-emerald-500" : "bg-red-500")} />
            <span className="text-[11px] font-medium text-slate-700 dark:text-slate-300">
              {health === null ? "Đang kiểm tra backend" : online ? "FastAPI online" : "Backend offline"}
            </span>
          </span>
          <span className={cn("font-mono text-[10px] font-semibold", aiStatus?.offline ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400")}>
            {aiStatus ? (aiStatus.offline ? "AI offline" : "AI on") : ""}
          </span>
        </div>
      </div>
    </aside>
  );
}
