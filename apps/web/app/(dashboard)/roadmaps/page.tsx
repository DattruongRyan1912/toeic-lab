"use client";

import { useState } from "react";
import Link from "next/link";
import { CheckCircle2, Crown, Shield, Target, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { WeeklyPlan } from "@/components/plan/weekly-plan";
import { api, errorMessage } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { formatDate, lessonHref, lessonNumbersIn } from "@/lib/format";
import { refreshLearner, useLearnerStore } from "@/lib/learner-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { Roadmap, SprintTask } from "@/types";

const TAB = "cursor-pointer px-3 py-2 text-xs text-slate-600 data-active:bg-emerald-600 data-active:text-white dark:text-slate-400 dark:data-active:text-white";

export default function RoadmapsPage() {
  const roadmap = useApi<Roadmap>("/roadmaps");
  const targetScore = useLearnerStore((state) => state.stats?.target_score);
  const authUser = useAuthStore((state) => state.user);
  const openLogin = useAuthStore((state) => state.openLogin);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [startDraft, setStartDraft] = useState<string | null>(null);
  const [savingStart, setSavingStart] = useState(false);

  if (roadmap.error) return <ErrorState message={roadmap.error} onRetry={roadmap.reload} />;
  if (!roadmap.data) return <LoadingState label="Đang tải lộ trình..." />;
  const data = roadmap.data;

  const toggle = async (task: SprintTask) => {
    if (!authUser) {
      toast.add({ title: "Yêu cầu đăng nhập", description: "Vui lòng đăng nhập tài khoản để đánh dấu hoàn thành nhiệm vụ.", type: "error" });
      openLogin();
      return;
    }
    setSavingId(task.id);
    try {
      const updated = await api<SprintTask>(`/roadmaps/tasks/${task.id}`, { method: "PATCH", json: { is_completed: !task.is_completed } });
      roadmap.mutate((prev) => {
        if (!prev) return prev;
        const tasks = prev.tasks.map((t) => (t.id === updated.id ? updated : t));
        const done = tasks.filter((t) => t.is_completed).length;
        return { ...prev, tasks, completed_tasks: done, progress_percent: tasks.length ? Math.round((done / tasks.length) * 100) : 0 };
      });
      void refreshLearner();
    } catch (err) {
      toast.add({ title: "Không cập nhật được nhiệm vụ", description: errorMessage(err), type: "error" });
    } finally {
      setSavingId(null);
    }
  };

  const saveStart = async () => {
    if (!startDraft) return;
    if (!authUser) {
      toast.add({ title: "Yêu cầu đăng nhập", description: "Vui lòng đăng nhập tài khoản để thay đổi ngày bắt đầu lộ trình.", type: "error" });
      openLogin();
      return;
    }
    setSavingStart(true);
    try {
      const updated = await api<Roadmap>("/roadmaps", { method: "PATCH", json: { start_date: startDraft } });
      roadmap.mutate(() => updated);
      setStartDraft(null);
      toast.add({ title: "Đã cập nhật ngày bắt đầu", description: `Bạn đang ở tuần ${updated.current_week}/${updated.total_weeks}`, type: "success" });
      void refreshLearner();
    } catch (err) {
      toast.add({ title: "Không lưu được", description: errorMessage(err), type: "error" });
    } finally {
      setSavingStart(false);
    }
  };

  // Phase titles, week ranges and score goals come from the API (rescaled with the exam date, goals from the learner's baseline).
  const byPhase = data.phases.map((p) => ({ ...p, tasks: data.tasks.filter((t) => t.phase === p.phase) }));

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col justify-between gap-6 rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50/80 via-white to-blue-50/60 p-6 md:flex-row md:items-center md:p-8 dark:border-emerald-500/20 dark:from-emerald-950/40 dark:via-slate-900 dark:to-blue-950/40">
        <div>
          <span className="rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-400">
            TUẦN {data.current_week}/{data.total_weeks} • PHASE {data.current_phase}
          </span>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{data.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <span>Bắt đầu: {formatDate(data.start_date)}/{data.start_date.slice(0, 4)}</span>
            <label className="sr-only" htmlFor="roadmap-start">Ngày bắt đầu lộ trình</label>
            <Input id="roadmap-start" type="date" value={startDraft ?? data.start_date} onChange={(e) => setStartDraft(e.target.value)} className="h-7 w-40 text-xs" />
            {startDraft && startDraft !== data.start_date && (
              <Button size="sm" disabled={savingStart} onClick={() => void saveStart()} className="h-7 cursor-pointer text-xs">
                Lưu
              </Button>
            )}
          </div>
        </div>
        <div className="min-w-[180px] shrink-0 rounded-xl border border-slate-200 bg-white p-4 text-right dark:border-slate-800 dark:bg-slate-900/80">
          <span className="block text-xs font-semibold text-slate-500 uppercase">Tiến độ lộ trình</span>
          <span className="text-3xl font-black text-emerald-600 dark:text-emerald-400">{data.progress_percent}%</span>
          <Progress value={data.progress_percent} className="mt-2 h-1.5" aria-label="Tiến độ lộ trình" />
          <span className="mt-1 block text-[11px] text-slate-500">
            {data.completed_tasks}/{data.total_tasks} nhiệm vụ
          </span>
        </div>
      </div>

      <WeeklyPlan />

      {data.exam_date && data.base_total_weeks && data.base_total_weeks !== data.total_weeks && (
        <p className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200">
          📅 Lộ trình {data.base_total_weeks} tuần đã được co giãn thành <strong>{data.total_weeks} tuần</strong> để kết thúc đúng ngày thi {formatDate(data.exam_date)}/{data.exam_date.slice(0, 4)}.
        </p>
      )}

      <Tabs defaultValue="personal" className="w-full space-y-6">
        <TabsList className="h-auto flex-wrap gap-1 border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900">
          <TabsTrigger value="personal" className={TAB}>
            <Target className="h-3.5 w-3.5" aria-hidden="true" /> Lộ trình của bạn (mục tiêu {targetScore ?? "…"}+)
          </TabsTrigger>
          <TabsTrigger value="sprint800" className={TAB}>
            <Zap className="h-3.5 w-3.5" aria-hidden="true" /> Sprint 8 tuần (750-850+)
          </TabsTrigger>
          <TabsTrigger value="sprint550" className={TAB}>
            <Shield className="h-3.5 w-3.5" aria-hidden="true" /> Sprint 6 tuần (550+)
          </TabsTrigger>
          <TabsTrigger value="sprint900" className={TAB}>
            <Crown className="h-3.5 w-3.5" aria-hidden="true" /> Sprint 6 tuần (900+)
          </TabsTrigger>
        </TabsList>

        <TabsContent value="personal" className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {byPhase.map((p) => {
              const current = p.phase === data.current_phase;
              const done = p.tasks.filter((t) => t.is_completed).length;
              return (
                <div
                  key={p.phase}
                  className={cn(
                    "space-y-2 rounded-xl border bg-white p-5 dark:bg-slate-900/60",
                    current ? "border-emerald-400 shadow-sm dark:border-emerald-500/50" : "border-slate-200 opacity-80 dark:border-slate-800",
                  )}
                >
                  <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                    Phase {p.phase}: Tuần {p.start_week} - {p.end_week} {current && "• đang học"}
                  </span>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">{p.title}</h2>
                  <p className="text-xs text-slate-600 dark:text-slate-400">{p.focus}</p>
                  <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                    {p.goal_score ? `Mục tiêu: ${p.goal_score}+ • ` : ""}
                    {done}/{p.tasks.length} nhiệm vụ
                  </p>
                </div>
              );
            })}
          </div>

          {byPhase.map((p) => (
            <Card key={p.phase} className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
              <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-700/60">
                <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" aria-hidden="true" /> Nhiệm vụ Phase {p.phase}
                </CardTitle>
                <span className="font-mono text-xs text-emerald-600 dark:text-emerald-400">
                  {p.tasks.filter((t) => t.is_completed).length}/{p.tasks.length} hoàn thành
                </span>
              </CardHeader>
              <CardContent className="space-y-3 pt-4">
                {p.tasks.map((task) => {
                  const overdue = !task.is_completed && !task.content_note && task.week_number < data.current_week;
                  const thisWeek = task.week_number === data.current_week;
                  const lessons = lessonNumbersIn(task.title);
                  return (
                    <div
                      key={task.id}
                      className={cn(
                        "flex items-start gap-3 rounded-xl border p-3.5 transition",
                        task.is_completed
                          ? "border-emerald-200 bg-emerald-50/40 dark:border-emerald-500/30 dark:bg-emerald-950/15"
                          : thisWeek
                            ? "border-blue-300 bg-blue-50/40 dark:border-blue-500/40 dark:bg-blue-950/20"
                            : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60",
                      )}
                    >
                      <input
                        id={`task-${task.id}`}
                        type="checkbox"
                        checked={task.is_completed}
                        disabled={savingId === task.id}
                        onChange={() => void toggle(task)}
                        className="mt-0.5 h-4 w-4 cursor-pointer rounded accent-emerald-600"
                      />
                      <div className="flex-1 space-y-1">
                        <label htmlFor={`task-${task.id}`} className="flex cursor-pointer flex-wrap items-center gap-2">
                          <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600 uppercase dark:bg-slate-800 dark:text-slate-300">
                            Tuần {task.week_number}
                          </span>
                          <span className="rounded border border-slate-200 px-1.5 text-[10px] text-slate-500 dark:border-slate-700">{task.category}</span>
                          {thisWeek && !task.is_completed && <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400">TUẦN NÀY</span>}
                          {overdue && <span className="text-[10px] font-bold text-red-500">TRỄ HẠN</span>}
                          <span className={cn("text-sm font-semibold", task.is_completed ? "text-slate-500 line-through" : "text-slate-900 dark:text-white")}>{task.title}</span>
                        </label>
                        <div className="flex flex-wrap gap-3 text-[11px] font-semibold">
                          {lessons.map((n) => (
                            <Link key={n} href={lessonHref(n)} className="text-blue-600 hover:underline dark:text-blue-400">
                              Mở Bài {String(n).padStart(2, "0")}
                            </Link>
                          ))}
                          {task.category === "Vocab" && <Link href="/vocab" className="text-blue-600 hover:underline dark:text-blue-400">Mở Sổ từ vựng</Link>}
                          {task.category === "Test" && <Link href="/mock-tests" className="text-blue-600 hover:underline dark:text-blue-400">Vào phòng thi</Link>}
                          {task.completed_at && <span className="font-normal text-slate-500">Xong {formatDate(task.completed_at)}</span>}
                          {task.base_week && task.base_week !== task.week_number && (
                            <span className="font-normal text-slate-400">(tuần {task.base_week} gốc)</span>
                          )}
                          {task.content_note && !task.is_completed && (
                            <span className="rounded-full bg-slate-100 px-2 font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                              ⏳ {task.content_note} — mốc chờ bổ sung học liệu
                            </span>
                          )}
                          {task.auto_met && !task.is_completed && task.evidence && (
                            <span className="rounded-full bg-emerald-50 px-2 font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                              ✓ {task.evidence} — có thể đánh dấu xong
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="sprint800">
          <Card className="space-y-3 border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">⚡ Sprint 8 tuần cấp tốc (750 - 850+)</h3>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Cho người đã đọc tốt tài liệu kỹ thuật, cần chứng chỉ trong 2 tháng: 80% thời gian giải đề ETS và chữa bẫy loại trừ. Dùng phòng thi thử mỗi ngày và giữ Sổ lỗi về 0 câu mở cuối mỗi tuần.
            </p>
          </Card>
        </TabsContent>
        <TabsContent value="sprint550">
          <Card className="space-y-3 border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">🔰 Sprint 6 tuần xây nền (550+)</h3>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Phản xạ nghe 100 câu Part 1 & 2, làm chủ 6 thì cơ bản (Bài 06) và vị trí từ loại (Bài 01). Mỗi ngày 15 thẻ SRS mới.
            </p>
          </Card>
        </TabsContent>
        <TabsContent value="sprint900">
          <Card className="space-y-3 border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">👑 Sprint 6 tuần Master (900+)</h3>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Xóa lỗi câu 120-130 Part 5 (Bài 08 rút gọn mệnh đề, Bài 09 giả định, Bài 10 đảo ngữ) và làm chủ Part 7 Triple Passages.
            </p>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
