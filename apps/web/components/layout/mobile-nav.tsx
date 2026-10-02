"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CheckSquare,
  Headphones,
  Layers,
  LayoutDashboard,
  Menu,
  X,
} from "lucide-react";
import { BrandLogo } from "@/components/brand/logo";
import { useLearnerStore } from "@/lib/learner-store";
import { cn } from "@/lib/utils";
import { NavSection, getSidebarNav, useBackendHealth } from "./sidebar";

export function MobileDrawer() {
  const pathname = usePathname();
  const mobileNavOpen = useLearnerStore((state) => state.mobileNavOpen);
  const setMobileNavOpen = useLearnerStore((state) => state.setMobileNavOpen);
  const stats = useLearnerStore((state) => state.stats);
  const aiStatus = useLearnerStore((state) => state.aiStatus);
  const health = useBackendHealth();

  const { studyNav, toolsNav } = getSidebarNav(stats, aiStatus);

  // Close drawer on route change
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname, setMobileNavOpen]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mobileNavOpen) {
        setMobileNavOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileNavOpen, setMobileNavOpen]);

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (mobileNavOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileNavOpen]);

  if (!mobileNavOpen) return null;

  const online = health?.ok ?? false;

  return (
    <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Menu điều hướng">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity duration-300 animate-in fade-in-0"
        onClick={() => setMobileNavOpen(false)}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div className="fixed inset-y-0 left-0 flex w-[85vw] max-w-xs flex-col bg-white shadow-2xl transition-transform duration-300 animate-in slide-in-from-left dark:bg-[#0d162a]">
        {/* Drawer Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-4 dark:border-slate-800/80">
          <Link
            href="/"
            onClick={() => setMobileNavOpen(false)}
            className="transition-opacity hover:opacity-95"
            aria-label="TOEIC Master Home"
          >
            <BrandLogo size={32} subtitle="SELF-STUDY LAB" />
          </Link>
          <button
            type="button"
            onClick={() => setMobileNavOpen(false)}
            className="cursor-pointer rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Đóng menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Drawer Nav Items */}
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Điều hướng di động">
          <NavSection
            title="Học Tập & Luyện Đề"
            items={studyNav}
            pathname={pathname}
            onItemClick={() => setMobileNavOpen(false)}
          />
          <div className="border-t border-slate-200 pt-3 dark:border-slate-800/70">
            <NavSection
              title="Công Cụ & Lộ Trình"
              items={toolsNav}
              pathname={pathname}
              onItemClick={() => setMobileNavOpen(false)}
            />
          </div>
        </nav>

        {/* Drawer Footer Status */}
        <div className="border-t border-slate-200 bg-slate-50 p-3 dark:border-slate-800/80 dark:bg-[#0a1020]">
          <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-2 text-xs dark:border-slate-700/50 dark:bg-slate-800/50">
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
      </div>
    </div>
  );
}

export function MobileBottomNav() {
  const pathname = usePathname();
  const setMobileNavOpen = useLearnerStore((state) => state.setMobileNavOpen);
  const mobileNavOpen = useLearnerStore((state) => state.mobileNavOpen);
  const stats = useLearnerStore((state) => state.stats);

  const tabs = [
    { label: "Tổng quan", href: "/", icon: LayoutDashboard },
    {
      label: "Từ vựng",
      href: "/vocab",
      icon: Layers,
      badge: stats?.srs_due_count ? stats.srs_due_count : null,
    },
    { label: "Luyện nghe", href: "/listening", icon: Headphones },
    { label: "Thi thử", href: "/mock-tests", icon: CheckSquare },
  ];

  return (
    <nav
      aria-label="Điều hướng nhanh thanh dưới cùng"
      className="fixed bottom-0 inset-x-0 z-40 flex h-16 items-center justify-around border-t border-slate-200/90 bg-white/95 px-1 pb-[env(safe-area-inset-bottom)] backdrop-blur-md transition-colors duration-200 select-none md:hidden dark:border-slate-800/90 dark:bg-[#0d162a]/95"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "relative flex flex-1 flex-col items-center justify-center py-1 text-center transition-all",
              active
                ? "text-blue-600 font-bold dark:text-blue-400"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200",
            )}
          >
            <div className="relative">
              <Icon className={cn("h-5 w-5", active ? "scale-110" : "scale-100")} />
              {tab.badge != null && Number(tab.badge) > 0 && (
                <span className="absolute -top-1 -right-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-600 px-1 text-[9px] font-bold text-white shadow-xs">
                  {tab.badge > 99 ? "99+" : tab.badge}
                </span>
              )}
            </div>
            <span className="mt-1 text-[10px] leading-none">{tab.label}</span>
          </Link>
        );
      })}

      {/* Menu / Drawer Toggle Button */}
      <button
        type="button"
        onClick={() => setMobileNavOpen(!mobileNavOpen)}
        className={cn(
          "relative flex flex-1 flex-col items-center justify-center py-1 text-center transition-all cursor-pointer",
          mobileNavOpen
            ? "text-blue-600 font-bold dark:text-blue-400"
            : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200",
        )}
        aria-label="Mở danh mục mở rộng"
      >
        <div className="relative">
          <Menu className={cn("h-5 w-5", mobileNavOpen && "scale-110")} />
          {stats && stats.open_errors > 0 && (
            <span className="absolute -top-0.5 -right-1 h-2 w-2 rounded-full bg-red-500" />
          )}
        </div>
        <span className="mt-1 text-[10px] leading-none">Thêm</span>
      </button>
    </nav>
  );
}
