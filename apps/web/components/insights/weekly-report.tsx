"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, Bot, CalendarRange, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState, LoadingState } from "@/components/states";
import { formatDate, percent } from "@/lib/format";
import { askMentor } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { WeeklyReport } from "@/types";

function shift(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function Delta({ value, unit = "" }: { value: number | null | undefined; unit?: string }) {
  if (value == null || value === 0) return null;
  const up = value > 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cn("inline-flex items-center text-[11px] font-semibold", up ? "text-emerald-600 dark:text-emerald-400" : "text-red-500")}>
      <Icon className="h-3 w-3" aria-hidden="true" />
      {up ? "+" : ""}
      {value}
      {unit}
    </span>
  );
}

function Stat({ label, value, hint, delta }: { label: string; value: React.ReactNode; hint?: string; delta?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="flex items-baseline gap-1.5 text-xl font-bold text-slate-900 dark:text-white">
        {value} {delta}
      </p>
      {hint && <p className="text-[10px] text-slate-500">{hint}</p>}
    </div>
  );
}

export function WeeklyReportCard() {
  const [end, setEnd] = useState<string | null>(null); // null = this week (server decides "today")
  const report = useApi<WeeklyReport>(`/learner/weekly-report${end ? `?end=${end}` : ""}`);

  if (report.error) return <ErrorState message={report.error} onRetry={report.reload} />;
  if (!report.data) return <LoadingState label="Đang tổng hợp báo cáo tuần..." />;
  const r = report.data;
  const accuracyDelta = r.practice.accuracy_delta == null ? null : Math.round(r.practice.accuracy_delta * 100);
  const changes = r.mastery_changes.filter((c) => Math.abs(c.delta) >= 0.03 || c.first_time);

  return (
    <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
            <CalendarRange className="h-5 w-5 text-blue-500" aria-hidden="true" /> Báo cáo tuần {formatDate(r.start)} – {formatDate(r.end)}
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button size="sm" variant="ghost" className="h-7 cursor-pointer px-2" onClick={() => setEnd(shift(r.end, -7))} aria-label="Tuần trước">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost" className="h-7 cursor-pointer px-2" disabled={end === null} onClick={() => setEnd(null)} aria-label="Về tuần này">
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 cursor-pointer text-xs"
              onClick={() => askMentor(`Phân tích báo cáo tuần ${formatDate(r.start)} – ${formatDate(r.end)} của tôi (dùng get_weekly_report) và đề xuất 3 thay đổi cụ thể cho kế hoạch tuần tới.`, { pageContext: "/analytics" })}
            >
              <Bot className="h-3.5 w-3.5 text-purple-500" aria-hidden="true" /> AI phân tích tuần
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {r.new_learner && (
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200">
            <span className="flex-1">Tuần đầu tiên của bạn — sau vài buổi học, báo cáo sẽ so sánh tiến bộ theo từng chuyên đề.</span>
            <Link href="/mock-tests?mode=smart" className="rounded-lg bg-blue-600 px-3 py-1.5 font-semibold text-white hover:bg-blue-500">Làm 15 câu đo năng lực</Link>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Thời gian học" value={`${r.study.minutes}'`} hint={r.study.goal_minutes ? `${percent(r.study.goal_rate)} mục tiêu • ${r.study.active_days}/${r.study.planned_days} ngày` : `${r.study.active_days} ngày có học`} />
          <Stat label="Độ chính xác" value={r.practice.questions ? percent(r.practice.accuracy) : "—"} hint={`${r.practice.questions} câu${r.practice.avg_seconds ? ` • ${r.practice.avg_seconds}s/câu` : ""}`} delta={<Delta value={accuracyDelta} unit="đ" />} />
          <Stat label="Câu sai" value={`${r.errors.mastered} nắm chắc`} hint={`${r.errors.new} mới • ${r.errors.open} còn mở`} />
          <Stat label="Điểm dự đoán" value={r.prediction.total} hint={`mục tiêu ${r.prediction.target}`} delta={<Delta value={r.prediction.delta} />} />
        </div>

        {changes.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200">Chuyên đề đã luyện trong tuần</p>
            <ul className="grid gap-1.5 sm:grid-cols-2">
              {changes.map((c) => (
                <li key={c.lesson_number} className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs dark:border-slate-700">
                  <Link href={`/lessons?lesson=${c.lesson_number}`} className="truncate font-medium text-slate-800 hover:underline dark:text-slate-200">{c.title}</Link>
                  <span className="flex shrink-0 items-center gap-1.5 font-mono">
                    {percent(c.mastery_before)} → <strong>{percent(c.mastery_after)}</strong>
                    <Delta value={Math.round(c.delta * 100)} unit="%" />
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="mb-1 text-xs font-semibold text-slate-800 dark:text-slate-200">Điểm nổi bật</p>
            {r.highlights.length ? (
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-slate-600 dark:text-slate-400">
                {r.highlights.map((line) => <li key={line}>{line}</li>)}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">Chưa có hoạt động học trong tuần này.</p>
            )}
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold text-slate-800 dark:text-slate-200">Tuần tới nên làm</p>
            <ul className="space-y-0.5 text-xs text-slate-600 dark:text-slate-400">
              {r.recommendations.map((line) => <li key={line}>→ {line}</li>)}
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
