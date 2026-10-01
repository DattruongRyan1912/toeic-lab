"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarClock, CheckCircle2, ChevronRight, Loader2, Pause, Play, Plus, RefreshCw, RotateCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { formatDate, percent } from "@/lib/format";
import { trackActivity, useStudyHeartbeat } from "@/lib/heartbeat";
import { refreshLearner } from "@/lib/learner-store";
import { askMentor } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { PlanDay, PlanItem, PlanWeek } from "@/types";

const SOURCE_BADGE: Record<string, string> = { user: "Bạn thêm", ai_mentor: "AI thêm", coach: "Gợi ý" };

function ListeningTimer({ item, onTracked }: { item: PlanItem; onTracked: () => void }) {
  const [running, setRunning] = useState(false);
  useStudyHeartbeat(
    running,
    async (seconds) => {
      await trackActivity("listening", seconds, `plan-${item.id}`);
      onTracked();
    },
    { explicit: true },
  );
  return (
    <Button
      size="sm"
      variant={running ? "default" : "outline"}
      onClick={() => setRunning((r) => !r)}
      className="h-7 cursor-pointer px-2.5 text-[11px]"
      aria-label={running ? `Dừng tính giờ ${item.title}` : `Bắt đầu tính giờ ${item.title}`}
    >
      {running ? <Pause className="h-3 w-3" aria-hidden="true" /> : <Play className="h-3 w-3" aria-hidden="true" />}
      {running ? "Đang tính giờ" : "Bắt đầu"}
    </Button>
  );
}

function ItemRow({ item, day, onChanged }: { item: PlanItem; day: PlanDay; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const patch = async (body: Record<string, unknown>, message: string) => {
    setBusy(true);
    try {
      await api(`/plan/items/${item.id}`, { method: "PATCH", json: body });
      toast.add({ title: message, description: item.title, type: "success" });
      onChanged();
      void refreshLearner();
    } catch (error) {
      toast.add({ title: "Không cập nhật được", description: errorMessage(error), type: "error" });
    } finally {
      setBusy(false);
    }
  };
  const moveToTomorrow = () => {
    const next = new Date(`${day.date}T00:00:00`);
    next.setDate(next.getDate() + 1);
    const iso = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`;
    void patch({ plan_date: iso }, "Đã dời sang ngày mai");
  };
  // planner items the learner moved become source "user" (kept on replan) but were not added by them
  const badge = item.source === "user" && item.kind !== "custom" ? "Bạn dời" : SOURCE_BADGE[item.source];
  const skipped = item.status === "skipped";
  const done = item.status === "done";
  const ratio = item.target_count ? Math.min(100, Math.round(((item.progress ?? 0) / item.target_count) * 100)) : null;

  return (
    <li className={cn("rounded-lg border p-2.5", done ? "border-emerald-200 bg-emerald-50/40 dark:border-emerald-500/20 dark:bg-emerald-950/10" : skipped ? "border-dashed border-slate-300 opacity-60 dark:border-slate-700" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900/50")}>
      <div className="flex items-start gap-2">
        {item.auto ? (
          <CheckCircle2 className={cn("mt-0.5 h-4 w-4 shrink-0", done ? "text-emerald-500" : "text-slate-300 dark:text-slate-600")} aria-label={done ? "Đã xong (tự động)" : "Tự đánh dấu khi bạn làm"} />
        ) : (
          <input
            type="checkbox"
            checked={done}
            disabled={busy || skipped}
            onChange={() => void patch({ status: done ? "pending" : "done" }, done ? "Đã mở lại" : "Đã hoàn thành")}
            aria-label={`Hoàn thành: ${item.title}`}
            className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-emerald-600"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded bg-slate-100 px-1.5 font-mono text-[9px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{item.tag}</span>
            <span className={cn("text-xs font-semibold", done || skipped ? "text-slate-500 line-through" : "text-slate-900 dark:text-white")}>{item.title}</span>
            <span className="text-[10px] text-slate-500">{item.estimated_minutes}&apos;</span>
            {badge && <span className="rounded-full bg-purple-50 px-1.5 text-[9px] font-semibold text-purple-700 dark:bg-purple-500/10 dark:text-purple-300">{badge}</span>}
          </div>
          {item.reason && <p className="mt-0.5 text-[10px] leading-snug text-slate-500 dark:text-slate-400">Vì sao: {item.reason}</p>}
          {ratio !== null && !skipped && (
            <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-500">
              <Progress value={ratio} className="h-1 flex-1" aria-label={`Tiến độ ${item.title}`} />
              {item.progress ?? 0}/{item.target_count}
            </div>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] font-semibold">
            {item.kind === "listening" && day.is_today && !done ? (
              <ListeningTimer item={item} onTracked={onChanged} />
            ) : item.kind === "ai_generate" ? (
              <button type="button" onClick={() => askMentor(item.detail ?? item.title, { pageContext: "/roadmaps" })} className="flex cursor-pointer items-center gap-1 text-purple-600 hover:underline dark:text-purple-400">
                <Sparkles className="h-3 w-3" aria-hidden="true" /> Nhờ AI làm ngay
              </button>
            ) : !done && !skipped && item.kind !== "custom" ? (
              <Link href={item.href} className="flex items-center gap-0.5 text-blue-600 hover:underline dark:text-blue-400">
                Làm ngay <ChevronRight className="h-3 w-3" aria-hidden="true" />
              </Link>
            ) : null}
            {!done && (
              skipped ? (
                <button type="button" disabled={busy} onClick={() => void patch({ status: "pending" }, "Đã khôi phục")} className="flex cursor-pointer items-center gap-1 text-slate-600 hover:underline dark:text-slate-400">
                  <RotateCcw className="h-3 w-3" aria-hidden="true" /> Khôi phục
                </button>
              ) : (
                <>
                  <button type="button" disabled={busy} onClick={moveToTomorrow} className="cursor-pointer text-slate-600 hover:underline dark:text-slate-400">Dời sang mai</button>
                  <button type="button" disabled={busy} onClick={() => void patch({ status: "skipped" }, "Đã bỏ qua")} className="cursor-pointer text-slate-500 hover:underline">Bỏ qua</button>
                </>
              )
            )}
          </div>
        </div>
      </div>
    </li>
  );
}

function AddItemForm({ days, onAdded }: { days: PlanDay[]; onAdded: () => void }) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(days[0]?.date ?? "");
  const [minutes, setMinutes] = useState(15);
  const [busy, setBusy] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (title.trim().length < 2) return;
    setBusy(true);
    try {
      await api("/plan/items", { method: "POST", json: { title: title.trim(), plan_date: date, estimated_minutes: minutes } });
      setTitle("");
      onAdded();
      void refreshLearner();
    } catch (error) {
      toast.add({ title: "Không thêm được nhiệm vụ", description: errorMessage(error), type: "error" });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
      <label className="sr-only" htmlFor="plan-title">Nhiệm vụ mới</label>
      <Input id="plan-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Thêm nhiệm vụ riêng, VD: Đọc 2 email Part 7" className="h-8 min-w-48 flex-1 text-xs" />
      <label className="sr-only" htmlFor="plan-date">Ngày</label>
      <select id="plan-date" value={date} onChange={(e) => setDate(e.target.value)} className="h-8 rounded-lg border border-slate-200 bg-transparent px-2 text-xs dark:border-slate-700">
        {days.map((d) => <option key={d.date} value={d.date}>{d.weekday} {formatDate(d.date)}</option>)}
      </select>
      <label className="sr-only" htmlFor="plan-minutes">Số phút</label>
      <Input id="plan-minutes" type="number" min={1} max={240} value={minutes} onChange={(e) => setMinutes(Number(e.target.value) || 15)} className="h-8 w-16 text-xs" />
      <Button type="submit" size="sm" disabled={busy || title.trim().length < 2} className="h-8 cursor-pointer">
        <Plus className="h-3.5 w-3.5" aria-hidden="true" /> Thêm
      </Button>
    </form>
  );
}

export function WeeklyPlan() {
  const week = useApi<PlanWeek>("/plan/week");
  const [replanning, setReplanning] = useState(false);
  const [selected, setSelected] = useState(0);
  const reload = week.reload;

  useEffect(() => {
    const onFocus = () => document.visibilityState === "visible" && reload();
    document.addEventListener("visibilitychange", onFocus);
    return () => document.removeEventListener("visibilitychange", onFocus);
  }, [reload]);

  if (week.error) return <ErrorState message={week.error} onRetry={week.reload} />;
  if (!week.data) return <LoadingState label="Đang lập kế hoạch..." />;
  const data = week.data;
  const day = data.days[selected] ?? data.days[0];

  const replan = async () => {
    setReplanning(true);
    try {
      const next = await api<PlanWeek>("/plan/replan", { method: "POST" });
      week.mutate(() => next);
      toast.add({ title: "Đã lập lại kế hoạch 7 ngày", description: "Dựa trên mức thành thạo, câu sai đến hạn và SRS mới nhất.", type: "success" });
      void refreshLearner();
    } catch (error) {
      toast.add({ title: "Không lập lại được", description: errorMessage(error), type: "error" });
    } finally {
      setReplanning(false);
    }
  };

  return (
    <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
              <CalendarClock className="h-5 w-5 text-blue-500" aria-hidden="true" /> Kế hoạch 7 ngày thích ứng
            </CardTitle>
            <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
              {data.settings.daily_minutes} phút/ngày • {data.settings.new_cards_per_day} thẻ mới/ngày
              {data.settings.days_to_exam != null ? ` • còn ${data.settings.days_to_exam} ngày đến kỳ thi` : " • chưa đặt ngày thi"}
              {" • "}
              <Link href="/settings#personalization" className="font-semibold text-blue-600 hover:underline dark:text-blue-400">chỉnh</Link>
            </p>
          </div>
          <Button size="sm" variant="outline" disabled={replanning} onClick={() => void replan()} className="cursor-pointer">
            {replanning ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
            Lập lại kế hoạch
          </Button>
        </div>
        {data.settings.adjustments.map((note) => (
          <p key={note} className="mt-2 rounded-lg bg-blue-50 px-3 py-1.5 text-[11px] text-blue-800 dark:bg-blue-500/10 dark:text-blue-300">
            🔧 Tự điều chỉnh: {note}. <Link href="/settings#personalization" className="font-semibold underline">Tắt tự điều chỉnh</Link>
          </p>
        ))}
        {data.history.planned_items > 0 && (
          <p className={cn("mt-2 rounded-lg px-3 py-1.5 text-[11px]", data.history.behind ? "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300" : "bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300")}>
            7 ngày qua: hoàn thành {data.history.done_items}/{data.history.planned_items} nhiệm vụ ({percent(data.history.completion_rate)}) • học {data.history.studied_minutes}/{data.history.goal_minutes} phút
            {data.history.behind ? " — kế hoạch đang quá tải, cân nhắc giảm phút/ngày hoặc thẻ mới." : ""}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-7 gap-1.5" role="tablist" aria-label="Chọn ngày">
          {data.days.map((d, index) => {
            const active = d.items.filter((i) => i.status !== "skipped");
            const doneCount = active.filter((i) => i.status === "done").length;
            return (
              <button
                key={d.date}
                type="button"
                role="tab"
                aria-selected={index === selected}
                onClick={() => setSelected(index)}
                className={cn(
                  "cursor-pointer rounded-lg border p-2 text-center transition",
                  index === selected ? "border-blue-500 bg-blue-50 dark:bg-blue-600/15" : "border-slate-200 dark:border-slate-700",
                  !d.is_study_day && "opacity-60",
                )}
              >
                <span className="block text-[10px] font-semibold text-slate-500">{d.is_today ? "Hôm nay" : d.weekday}</span>
                <span className="block text-xs font-bold text-slate-900 dark:text-white">{formatDate(d.date)}</span>
                <span className="block text-[10px] text-slate-500">{d.is_study_day ? `${d.planned_minutes}'` : "Nghỉ"}</span>
                {active.length > 0 && <span className="block text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">{doneCount}/{active.length}</span>}
              </button>
            );
          })}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {day.weekday} {formatDate(day.date)} • dự kiến {day.planned_minutes} phút
              {day.is_today ? ` • đã học ${day.studied_minutes} phút` : ""}
            </span>
          </div>
          {day.items.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500 dark:border-slate-700">
              {day.is_study_day ? "Chưa có nhiệm vụ." : "Ngày nghỉ theo lịch học của bạn."}
            </p>
          ) : (
            <ul className="space-y-2">
              {day.items.map((item) => <ItemRow key={item.id} item={item} day={day} onChanged={week.reload} />)}
            </ul>
          )}
        </div>

        <AddItemForm days={data.days} onAdded={week.reload} />

        {data.focus.length > 0 && (
          <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-700">
            <p className="mb-1.5 font-semibold text-slate-800 dark:text-slate-200">Chuyên đề trọng tâm tuần này</p>
            <ul className="space-y-1">
              {data.focus.map((f) => (
                <li key={f.lesson_number} className="flex flex-wrap justify-between gap-2">
                  <Link href={`/lessons?lesson=${f.lesson_number}`} className="font-semibold text-blue-600 hover:underline dark:text-blue-400">{f.title}</Link>
                  <span className="text-slate-500">{f.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
