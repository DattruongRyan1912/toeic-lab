"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Calendar,
  CheckCircle2,
  CheckSquare,
  ChevronRight,
  Clock,
  Flame,
  GraduationCap,
  Layers,
  Sparkles,
  Target,
  Timer,
  TrendingUp,
  Wand2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { SuggestionList } from "@/components/coach/suggestion-list";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { ERROR_TYPES, LESSON_STATUS, formatDate, lessonHref, percent } from "@/lib/format";
import { refreshLearner, useLearnerStore } from "@/lib/learner-store";
import { askMentor } from "@/lib/mentor-store";
import { cn } from "@/lib/utils";
import type { Suggestion, TodayTask } from "@/types";

const CARD = "bg-white border-slate-200 shadow-2xs dark:bg-slate-800/80 dark:border-slate-700/70";
const SEVERITY_STYLE: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/30",
  high: "bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-500/15 dark:text-orange-300 dark:border-orange-500/30",
  medium: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30",
  low: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700/40 dark:text-slate-300 dark:border-slate-600/60",
};

function MetricCard({
  href,
  label,
  value,
  detail,
  icon: Icon,
  tone,
  children,
}: {
  href: string;
  label: string;
  value: string | number;
  detail?: string;
  icon: typeof Clock;
  tone: string;
  children?: React.ReactNode;
}) {
  return (
    <Link href={href} className="group block min-w-0">
      <Card className={cn(CARD, "p-3 sm:p-5 h-full flex flex-col justify-between transition-all group-hover:border-blue-400 dark:group-hover:border-blue-500/60")}>
        <div>
          <div className="mb-2 sm:mb-3 flex items-center justify-between gap-1">
            <span className="text-[10px] sm:text-[11px] font-bold tracking-wider text-slate-500 uppercase dark:text-slate-400 truncate">{label}</span>
            <div className={cn("flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-lg border", tone)}>
              <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" aria-hidden="true" />
            </div>
          </div>
          <div className="font-mono text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100">{value}</div>
          {detail && <p className="mt-1.5 sm:mt-2 text-[10px] sm:text-xs text-slate-500 dark:text-slate-400 leading-snug break-words">{detail}</p>}
        </div>
        {children}
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const stats = useLearnerStore((state) => state.stats);
  const error = useLearnerStore((state) => state.error);
  const [savingTask, setSavingTask] = useState<string | null>(null);
  const suggestions = useApi<Suggestion[]>("/learner/suggestions");

  useEffect(() => {
    void refreshLearner();
  }, []);

  if (!stats) {
    return error ? <ErrorState message={error} onRetry={() => void refreshLearner()} /> : <LoadingState label="Đang tải bảng điều khiển..." />;
  }

  const setTaskStatus = async (task: TodayTask, status: "done" | "skipped" | "pending") => {
    setSavingTask(task.key);
    try {
      if (task.plan_item_id) {
        await api(`/plan/items/${task.plan_item_id}`, { method: "PATCH", json: { status } });
      } else {
        const id = Number(task.key.replace("roadmap-", ""));
        await api(`/roadmaps/tasks/${id}`, { method: "PATCH", json: { is_completed: status === "done" } });
      }
      toast.add({ title: status === "skipped" ? "Đã bỏ qua nhiệm vụ" : status === "done" ? "Đã hoàn thành" : "Đã mở lại", description: task.title, type: "success" });
      await refreshLearner();
      suggestions.reload();
    } catch (err) {
      toast.add({ title: "Không cập nhật được nhiệm vụ", description: errorMessage(err), type: "error" });
    } finally {
      setSavingTask(null);
    }
  };

  const pastDays = stats.activity_week.filter((day) => !day.is_future);
  const activeDays = pastDays.filter((day) => day.active).length;
  const rcaMax = Math.max(1, ...Object.values(stats.rca_breakdown));
  const tasksDone = stats.today_tasks.filter((task) => task.done).length;
  const predicted = stats.predicted_score;
  const goalPercent = Math.min(100, Math.round((stats.study_minutes_today / Math.max(1, stats.daily_goal_minutes)) * 100));
  const rec = stats.recommended_lesson;

  return (
    <div className="space-y-6">
      {!stats.onboarded && (
        <Link
          href="/onboarding"
          className="flex items-center justify-between gap-3 rounded-2xl border border-purple-300 bg-gradient-to-r from-purple-50 to-blue-50 p-4 text-sm transition hover:shadow-md dark:border-purple-500/40 dark:from-purple-950/40 dark:to-blue-950/40"
        >
          <span className="flex items-center gap-3">
            <Wand2 className="h-5 w-5 shrink-0 text-purple-600 dark:text-purple-400" aria-hidden="true" />
            <span>
              <strong className="text-slate-900 dark:text-white">Cá nhân hoá lộ trình trong 2 phút</strong>
              <span className="block text-xs text-slate-600 dark:text-slate-400">
                Ngày thi, điểm hiện tại và thời gian rảnh → kế hoạch hằng ngày, dự đoán điểm và AI Mentor bám theo bạn.
              </span>
            </span>
          </span>
          <ChevronRight className="h-4 w-4 shrink-0 text-purple-600" aria-hidden="true" />
        </Link>
      )}

      {/* Hero */}
      <div className="relative overflow-hidden rounded-2xl border border-blue-200/80 bg-gradient-to-r from-blue-50/90 via-indigo-50/50 to-white p-5 sm:p-6 shadow-xs md:p-8 dark:border-slate-700/70 dark:from-slate-800 dark:via-slate-800/95 dark:to-slate-800/90">
        <div className="relative z-10 flex flex-col justify-between gap-5 sm:gap-6 lg:flex-row lg:items-center">
          <div className="space-y-2.5 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-100 px-2.5 sm:px-3 py-1 font-semibold text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/15 dark:text-blue-300">
                <Flame className="h-3.5 w-3.5 fill-orange-500 text-orange-500 shrink-0" aria-hidden="true" />
                Phase {stats.current_phase} • Tuần {stats.current_week}/{stats.total_weeks}
              </span>
              <span className="text-slate-600 dark:text-slate-300 font-medium">
                • Mục tiêu: {stats.target_score}+ <span className="hidden sm:inline">({stats.target_cefr})</span>
              </span>
              {stats.days_to_exam != null && (
                <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[11px] font-semibold text-red-700 dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-300">
                  Còn {stats.days_to_exam} ngày thi
                </span>
              )}
              {stats.headline && (
                <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300">
                  {stats.headline}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl md:text-4xl dark:text-slate-100 break-words">
              Chào mừng trở lại, {stats.display_name}! 👋
            </h1>
            <p className="max-w-2xl text-xs leading-relaxed text-slate-600 sm:text-sm dark:text-slate-300 break-words">
              Kế hoạch hôm nay: <strong>{stats.today_tasks.length} nhiệm vụ (~{stats.today_plan_minutes} phút)</strong>, đã học{" "}
              <strong>{stats.study_minutes_today}/{stats.daily_goal_minutes} phút</strong>
              {stats.error_reviews_due ? (
                <>
                  , <strong>{stats.error_reviews_due} câu sai</strong> đến hạn ôn
                </>
              ) : null}
              {rec ? (
                <>
                  . Trọng tâm: <strong>{rec.title}</strong> — {rec.reason.toLowerCase()}.
                </>
              ) : (
                "."
              )}
            </p>
          </div>
          <div className="z-10 flex shrink-0 flex-wrap items-center gap-2 sm:gap-3">
            <Link href="/vocab" className="flex-1 sm:flex-initial">
              <Button className="w-full sm:w-auto flex h-10 cursor-pointer items-center justify-center gap-2 bg-blue-600 px-4 sm:px-5 text-xs font-semibold text-white hover:bg-blue-500">
                <Layers className="h-4 w-4 shrink-0" aria-hidden="true" /> Ôn {stats.srs_due_count} thẻ SRS
              </Button>
            </Link>
            <Link href={stats.error_reviews_due ? "/mock-tests?mode=review" : "/mock-tests?mode=smart"} className="flex-1 sm:flex-initial">
              <Button variant="outline" className="w-full sm:w-auto flex h-10 cursor-pointer items-center justify-center gap-2 px-3 sm:px-4 text-xs">
                <CheckSquare className="h-4 w-4 shrink-0 text-purple-600 dark:text-purple-400" aria-hidden="true" />
                {stats.error_reviews_due ? `Ôn ${stats.error_reviews_due} câu sai` : "Luyện thông minh"}
              </Button>
            </Link>
            {rec && (
              <Link href={lessonHref(rec.lesson_number)} className="w-full sm:w-auto">
                <Button variant="outline" className="w-full sm:w-auto flex h-10 cursor-pointer items-center justify-center gap-2 px-4 text-xs">
                  <GraduationCap className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" /> Bài {String(rec.lesson_number).padStart(2, "0")}
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <MetricCard
          href="/vocab"
          label="Thẻ SRS cần học"
          value={stats.srs_due_count}
          detail={`${stats.srs_review_due} đến hạn + ${stats.srs_new_available} thẻ mới • đã ôn ${stats.srs_reviewed_today} hôm nay`}
          icon={Clock}
          tone="bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/30"
        />
        <MetricCard
          href="/analytics"
          label="Điểm dự đoán"
          value={predicted ? predicted.total : "—"}
          detail={
            predicted
              ? `Khoảng ${predicted.low}–${predicted.high} • Tin cậy ${Math.round(predicted.confidence * 100)}%${
                  predicted.questions_needed_to_narrow && predicted.questions_needed_to_narrow > 0
                    ? ` (cần thêm ${predicted.questions_needed_to_narrow} câu)`
                    : predicted.basis_reading === "prior"
                      ? " (chưa có dữ liệu)"
                      : ""
                }`
              : "Làm bài luyện để có dự đoán"
          }
          icon={Target}
          tone="bg-purple-50 text-purple-600 border-purple-200 dark:bg-purple-500/15 dark:text-purple-400 dark:border-purple-500/30"
        />
        <MetricCard
          href="/roadmaps"
          label="Tiến độ lộ trình"
          value={`${stats.roadmap_percent}%`}
          detail={`${stats.completed_tasks}/${stats.total_tasks} nhiệm vụ • Tuần ${stats.current_week}`}
          icon={TrendingUp}
          tone="bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-500/15 dark:text-blue-400 dark:border-blue-500/30"
        >
          <Progress value={stats.roadmap_percent} className="mt-2 h-1.5" aria-label="Tiến độ lộ trình" />
        </MetricCard>
        <MetricCard
          href="/analytics"
          label="Thời gian học hôm nay"
          value={`${stats.study_minutes_today}'`}
          detail={`Mục tiêu ${stats.daily_goal_minutes}' • tuần này ${stats.study_minutes_week}'`}
          icon={Timer}
          tone="bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/30"
        >
          <Progress value={goalPercent} className="mt-2 h-1.5" aria-label="Tiến độ mục tiêu phút học hôm nay" />
        </MetricCard>
      </div>

      {/* Weekly activity */}
      <Card className={cn(CARD, "p-3.5 sm:p-5 overflow-hidden")}>
        <div className="mb-3 sm:mb-4 flex flex-col justify-between gap-1.5 sm:gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" aria-hidden="true" />
            <h2 className="text-xs font-bold tracking-wider text-slate-800 uppercase dark:text-slate-200">Hoạt động tuần này</h2>
          </div>
          <span className="font-mono text-[11px] sm:text-xs font-semibold text-slate-600 dark:text-slate-400">
            {activeDays}/{pastDays.length} ngày có học • chuỗi {stats.streak_days} ngày
          </span>
        </div>
        <div className="overflow-x-auto no-scrollbar -mx-1 px-1 sm:mx-0 sm:px-0">
          <div className="grid min-w-[480px] sm:min-w-0 grid-cols-7 gap-1.5 sm:gap-2">
            {stats.activity_week.map((day) => {
              const fullDetails = day.is_future
                ? undefined
                : [
                    day.minutes > 0 ? `${day.minutes} phút học` : null,
                    day.srs_reviews > 0 ? `${day.srs_reviews} thẻ SRS` : null,
                    day.questions_answered > 0 ? `${day.questions_answered} câu hỏi` : null,
                    day.errors_logged > 0 ? `${day.errors_logged} lỗi` : null,
                    day.tasks_completed > 0 ? `${day.tasks_completed} nhiệm vụ` : null,
                    day.mentor_questions > 0 ? `${day.mentor_questions} câu hỏi AI` : null,
                  ]
                    .filter(Boolean)
                    .join(" • ") || (day.is_today ? "Chưa có hoạt động hôm nay" : "Nghỉ ngơi");

              return (
                <div
                  key={day.date}
                  title={fullDetails}
                  className={cn(
                    "rounded-xl border p-2 sm:p-3 text-center transition-all flex flex-col justify-between min-h-[72px] sm:min-h-[80px]",
                    day.is_today
                      ? "border-blue-500 bg-blue-50/80 text-blue-900 ring-1 ring-blue-500/30 dark:bg-blue-600/15 dark:text-white dark:border-blue-400"
                      : day.active
                        ? "border-emerald-300 bg-emerald-50/40 dark:border-emerald-500/30 dark:bg-slate-800"
                        : "border-slate-200 bg-slate-50 dark:border-slate-700/40 dark:bg-slate-900/40",
                  )}
                >
                  <div>
                    <span className="block font-mono text-[10px] font-semibold text-slate-500 dark:text-slate-400">
                      {day.weekday}
                    </span>
                    <span
                      className={cn(
                        "my-0.5 block text-xs sm:text-sm font-bold",
                        day.active ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400",
                      )}
                    >
                      {formatDate(day.date)}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-center">
                    {day.is_future ? (
                      <span className="text-[10px] text-slate-300 dark:text-slate-600">—</span>
                    ) : day.active ? (
                      <span className="inline-flex items-center justify-center gap-0.5 rounded-md bg-emerald-100/80 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 max-w-full truncate">
                        ✓ {day.minutes > 0 ? `${day.minutes}'` : day.questions_answered > 0 ? `${day.questions_answered} câu` : `${day.total} mục`}
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 truncate">
                        {day.is_today ? "Hôm nay" : "Nghỉ"}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-7">
          {/* Today's tasks */}
          <Card className={CARD}>
            <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-700/60">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" /> Nhiệm vụ trọng tâm hôm nay
                </CardTitle>
                <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                  Lập từ dữ liệu học của bạn • tự đánh dấu xong khi bạn làm •{" "}
                  <Link href="/roadmaps" className="font-semibold text-blue-600 hover:underline dark:text-blue-400">xem cả tuần</Link>
                </p>
              </div>
              <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-xs font-semibold text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300">
                {tasksDone}/{stats.today_tasks.length} xong
              </span>
            </CardHeader>
            <CardContent className="space-y-2.5 pt-4">
              {stats.today_tasks.length === 0 && (
                <p className="py-4 text-center text-xs text-slate-500">Hôm nay là ngày nghỉ theo lịch học của bạn. Nghỉ ngơi cũng là một phần của kế hoạch 🌿</p>
              )}
              {stats.today_tasks.map((task) => {
                const manual = !task.auto;
                const percentDone = task.target ? Math.min(100, Math.round(((task.progress ?? 0) / task.target) * 100)) : null;
                return (
                  <div
                    key={task.key}
                    className={cn(
                      "rounded-xl border p-3.5 transition-all",
                      task.done
                        ? "border-emerald-200 bg-emerald-50/30 dark:border-emerald-500/20 dark:bg-slate-900/40"
                        : "border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2.5 sm:gap-3">
                      <div className="flex min-w-0 flex-1 items-start sm:items-center gap-2.5 sm:gap-3">
                        {manual ? (
                          <input
                            type="checkbox"
                            checked={task.done}
                            disabled={savingTask === task.key}
                            onChange={() => void setTaskStatus(task, task.done ? "pending" : "done")}
                            aria-label={`Đánh dấu hoàn thành: ${task.title}`}
                            className="mt-0.5 sm:mt-0 h-4 w-4 shrink-0 cursor-pointer rounded accent-emerald-600"
                          />
                        ) : (
                          <CheckCircle2
                            className={cn("mt-0.5 sm:mt-0 h-4 w-4 shrink-0", task.done ? "text-emerald-500" : "text-slate-300 dark:text-slate-600")}
                            aria-label={task.done ? "Đã xong (tự động)" : "Tự đánh dấu khi bạn làm"}
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap sm:flex-nowrap items-center gap-1.5 sm:gap-2">
                            <span className="rounded border border-slate-200 bg-slate-100 px-1.5 font-mono text-[10px] font-semibold text-slate-600 shrink-0 dark:border-slate-600/60 dark:bg-slate-700/60 dark:text-slate-300">
                              {task.tag}
                            </span>
                            <span className={cn("text-xs font-semibold break-words", task.done ? "text-slate-500 line-through" : "text-slate-800 dark:text-slate-100")}>
                              {task.title}
                            </span>
                            {task.estimated_minutes ? <span className="shrink-0 text-[10px] text-slate-500 font-mono">~{task.estimated_minutes}&apos;</span> : null}
                          </div>
                          {(task.reason || task.detail) && (
                            <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400 break-words line-clamp-2" title={task.reason ?? task.detail ?? undefined}>
                              {task.reason ? `Vì sao: ${task.reason}` : task.detail}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        {!task.done && task.plan_item_id && (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={savingTask === task.key}
                            onClick={() => void setTaskStatus(task, "skipped")}
                            className="h-7 cursor-pointer px-2 text-[11px] text-slate-500"
                            aria-label={`Bỏ qua: ${task.title}`}
                          >
                            Bỏ qua
                          </Button>
                        )}
                        <Link href={task.href}>
                          <Button size="sm" variant="ghost" className="h-7 cursor-pointer px-2.5 text-xs text-blue-600 dark:text-blue-400">
                            {task.done ? "Xem lại" : "Làm ngay"} <ChevronRight className="ml-0.5 h-3 w-3" aria-hidden="true" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                    {percentDone !== null && !task.done && (task.progress ?? 0) > 0 && (
                      <div className="mt-2 flex items-center gap-2 pl-7 text-[10px] text-slate-500">
                        <Progress value={percentDone} className="h-1 flex-1" aria-label={`Tiến độ ${task.title}`} />
                        <span>{task.progress}/{task.target}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* RCA breakdown */}
          <Card className={CARD}>
            <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-700/60">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" /> Phân loại lỗi sai theo 5 RCA
                </CardTitle>
                <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{stats.total_errors} câu trong Sổ lỗi (tự ghi từ bài thi thử & AI Mentor)</p>
              </div>
              <Link href="/error-log">
                <Button variant="ghost" size="sm" className="h-7 cursor-pointer px-2 text-xs text-blue-600 dark:text-blue-400">
                  Sổ lỗi <ArrowRight className="ml-1 h-3 w-3" aria-hidden="true" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-3.5 pt-4">
              {ERROR_TYPES.map((rca) => {
                const count = stats.rca_breakdown[rca.key] ?? 0;
                return (
                  <Link key={rca.key} href={`/error-log?type=${rca.key}`} className="block space-y-1 rounded-lg p-1 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        <span className={cn("font-mono font-bold", rca.color)}>[{rca.key}]</span> {rca.label}
                      </span>
                      <span className="font-mono font-bold text-slate-700 dark:text-slate-300">{count} câu</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900">
                      <div className={cn(rca.bar, "h-1.5 rounded-full")} style={{ width: `${count ? Math.max(4, (count / rcaMax) * 100) : 0}%` }} />
                    </div>
                  </Link>
                );
              })}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6 lg:col-span-5">
          {/* Coach suggestions */}
          <Card className={cn(CARD, "space-y-3 p-5")}>
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-xs font-bold tracking-wider text-slate-900 uppercase dark:text-slate-100">
                <Sparkles className="h-4 w-4 text-amber-500" aria-hidden="true" /> Gợi ý từ dữ liệu của bạn
              </h2>
              <span className="text-[10px] text-slate-500">1 chạm • có hoàn tác</span>
            </div>
            {suggestions.error ? (
              <ErrorState message={suggestions.error} onRetry={suggestions.reload} />
            ) : !suggestions.data ? (
              <LoadingState label="Đang phân tích..." />
            ) : (
              <SuggestionList suggestions={suggestions.data} onChanged={suggestions.reload} />
            )}
          </Card>

          {/* Recommended lesson */}
          {rec && (
            <Card className="relative overflow-hidden border-blue-200 bg-gradient-to-br from-blue-50/60 to-white p-5 shadow-2xs dark:border-slate-700/70 dark:from-slate-800 dark:to-slate-800/80">
              <div className="mb-2 flex items-center justify-between">
                <span className="rounded border border-blue-200 bg-blue-50 px-2 py-0.5 font-mono text-[10px] font-bold tracking-wider text-blue-700 uppercase dark:border-blue-500/30 dark:bg-blue-500/15 dark:text-blue-300">
                  Chuyên đề nên học
                </span>
                <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-semibold", LESSON_STATUS[rec.status].style)}>
                  {LESSON_STATUS[rec.status].label}
                  {rec.accuracy != null ? ` • ${percent(rec.accuracy)}` : ""}
                </span>
              </div>
              <h2 className="mt-1 text-base font-bold text-slate-900 dark:text-slate-100 break-words">{rec.title}</h2>
              {rec.subtitle && <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 break-words">{rec.subtitle}</p>}
              {rec.syntax_formula && (
                <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3 text-xs dark:border-slate-700/60 dark:bg-slate-900/60">
                  <p className="font-semibold text-emerald-600 dark:text-emerald-400">💡 Công thức cốt lõi</p>
                  <p className="mt-1 font-mono text-slate-700 dark:text-slate-300 break-words whitespace-pre-wrap">{rec.syntax_formula}</p>
                </div>
              )}
              <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 break-words">Lý do: {rec.reason}</p>
              <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-200 pt-3 dark:border-slate-700/60">
                {rec.question_count > 0 ? (
                  <Link href={`/mock-tests?lesson=${rec.lesson_number}`} className="text-[11px] font-semibold text-purple-600 hover:underline dark:text-purple-400">
                    Luyện {rec.question_count} câu liên quan →
                  </Link>
                ) : (
                  <span className="text-[11px] text-slate-500">Chưa có câu luyện trong ngân hàng đề</span>
                )}
                <Link href={lessonHref(rec.lesson_number)}>
                  <Button size="sm" className="flex h-8 cursor-pointer items-center gap-1.5 bg-blue-600 px-3.5 text-xs text-white hover:bg-blue-500 shrink-0">
                    Mở bài học <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </Link>
              </div>
            </Card>
          )}

          {/* Learning gaps */}
          <Card className={cn(CARD, "space-y-3.5 p-5")}>
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-purple-600 dark:text-purple-400" aria-hidden="true" />
              <h2 className="text-xs font-bold tracking-wider text-slate-900 uppercase dark:text-slate-100">Lỗ hổng cần bịt ngay</h2>
            </div>
            {stats.learning_gaps.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                Chưa có lỗ hổng nào. Làm một bài <Link href="/mock-tests" className="font-semibold text-blue-600 dark:text-blue-400">luyện Part 5</Link> — câu sai sẽ tự vào Sổ lỗi và được gom thành lỗ hổng theo chuyên đề.
              </div>
            ) : (
              <div className="space-y-2">
                {stats.learning_gaps.map((gap, index) => (
                  <div key={gap.id} className="space-y-1.5 rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-xs dark:border-slate-700/60 dark:bg-slate-900/40">
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2.5 min-w-0">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-red-200 bg-red-50 font-mono text-[10px] font-bold text-red-600 dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-400">
                          {index + 1}
                        </span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200 break-words">{gap.topic}</span>
                      </span>
                      <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-semibold shrink-0", SEVERITY_STYLE[gap.severity] ?? SEVERITY_STYLE.medium)}>
                        {gap.error_count} lỗi
                      </span>
                    </div>
                    {gap.ai_recommendation && <p className="text-[11px] text-slate-500 dark:text-slate-400 break-words">{gap.ai_recommendation}</p>}
                    <div className="flex gap-3 text-[11px] font-semibold">
                      {gap.lesson_number && (
                        <Link href={lessonHref(gap.lesson_number)} className="text-blue-600 hover:underline dark:text-blue-400">
                          Ôn Bài {String(gap.lesson_number).padStart(2, "0")}
                        </Link>
                      )}
                      <button
                        type="button"
                        className="cursor-pointer text-purple-600 hover:underline dark:text-purple-400"
                        onClick={() =>
                          askMentor(`Tôi hay sai dạng "${gap.topic}" (${gap.error_count} câu chưa khắc phục). Phân tích nguyên nhân và cho tôi quy tắc nhận diện nhanh kèm 2 câu luyện.`, {
                            pageContext: "/",
                          })
                        }
                      >
                        Hỏi AI Mentor
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
