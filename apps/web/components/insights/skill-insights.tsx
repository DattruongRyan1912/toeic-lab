"use client";

import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, Brain, Clock, Gauge, Layers, Sparkles, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState, LoadingState } from "@/components/states";
import { formatDate, LESSON_STATUS, percent } from "@/lib/format";
import { askMentor } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { LearnerInsights, SectionPrediction, SkillStat } from "@/types";

const CARD = "border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80";
const BASIS: Record<SectionPrediction["basis"], string> = {
  data: "từ bài làm của bạn",
  partial: "từ bài làm, một số Part ngoại suy",
  baseline: "từ điểm đầu vào",
  prior: "ước lượng mặc định",
};
const KIND_LABELS: Record<string, string> = {
  srs: "SRS", practice: "Luyện đề", review: "Ôn lỗi", lesson: "Bài học", mentor: "AI Mentor", listening: "Listening", reading: "Reading", other: "Khác",
};

function MasteryBar({ stat }: { stat: SkillStat }) {
  const value = Math.round(stat.mastery * 100);
  const color = stat.attempts === 0 ? "bg-slate-300 dark:bg-slate-600" : value >= 80 ? "bg-emerald-500" : value >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900" role="img" aria-label={`Mastery ${value}%`}>
      <div className={cn("h-2 rounded-full", color, stat.attempts === 0 && "opacity-50")} style={{ width: `${value}%` }} />
    </div>
  );
}

function Trend({ value }: { value: number | null }) {
  if (value === null || Math.abs(value) < 0.05) return null;
  const up = value > 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cn("inline-flex items-center text-[10px] font-semibold", up ? "text-emerald-600" : "text-red-500")}>
      <Icon className="h-3 w-3" aria-hidden="true" />
      {up ? "+" : ""}
      {Math.round(value * 100)}%
    </span>
  );
}

function SectionBox({ label, data, tone }: { label: string; data: SectionPrediction; tone: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <span className="text-xs text-slate-500">{label}</span>
      <p className={cn("mt-1 text-3xl font-extrabold", tone)}>{data.expected}</p>
      <p className="text-[11px] text-slate-500">khoảng {data.low}-{data.high}</p>
      <p className="mt-1 text-[10px] text-slate-400">{BASIS[data.basis]} • tin cậy {Math.round(data.confidence * 100)}%</p>
    </div>
  );
}

export function SkillInsights() {
  const insights = useApi<LearnerInsights>("/learner/insights");
  if (insights.error) return <ErrorState message={insights.error} onRetry={insights.reload} />;
  if (!insights.data) return <LoadingState label="Đang phân tích quá trình học..." />;
  const data = insights.data;
  const p = data.prediction;
  const scale = (value: number) => `${Math.min(100, Math.max(0, ((value - 10) / 980) * 100))}%`;
  const maxMinutes = Math.max(1, ...data.study_minutes.map((d) => Math.max(d.minutes, d.goal_minutes)));
  const studiedDays = data.study_minutes.filter((d) => d.minutes > 0).length;
  const totalMinutes = data.study_minutes.reduce((sum, d) => sum + d.minutes, 0);
  const lessons = [...data.lessons].sort((a, b) => (a.lesson_number ?? 0) - (b.lesson_number ?? 0));
  const parts = data.parts.filter((s) => s.attempts > 0 || s.question_count > 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-12">
        <Card className={cn(CARD, "lg:col-span-7")}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
              <Target className="h-5 w-5 text-purple-500" aria-hidden="true" /> Điểm dự đoán nếu thi hôm nay
            </CardTitle>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Từ {data.total_attempts} câu bạn đã làm (câu gần đây có trọng số cao hơn). Khoảng càng hẹp khi bạn luyện càng nhiều.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-end gap-3">
              <span className="text-5xl font-black text-slate-900 dark:text-white">{p.total.expected}</span>
              <span className="pb-1 text-sm text-slate-500">/ 990 • {p.total.cefr}</span>
            </div>
            <div className="relative h-3 rounded-full bg-slate-100 dark:bg-slate-900" role="img" aria-label={`Khoảng ${p.total.low} đến ${p.total.high}, mục tiêu ${p.target_score}`}>
              <div className="absolute h-3 rounded-full bg-purple-300/70 dark:bg-purple-500/40" style={{ left: scale(p.total.low), width: `calc(${scale(p.total.high)} - ${scale(p.total.low)})` }} />
              <div className="absolute top-[-3px] h-[18px] w-1 rounded bg-purple-700 dark:bg-purple-300" style={{ left: scale(p.total.expected) }} />
              <div className="absolute top-[-6px] h-6 w-0.5 bg-red-500" style={{ left: scale(p.target_score) }} />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>Khoảng {p.total.low}-{p.total.high} • tin cậy {Math.round(p.confidence * 100)}%</span>
              <span className="font-semibold text-red-500">Mục tiêu {p.target_score}{p.target_gap > 0 ? ` (còn ${p.target_gap})` : " ✓"}</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <SectionBox label="Listening" data={p.listening} tone="text-blue-600 dark:text-blue-400" />
              <SectionBox label="Reading" data={p.reading} tone="text-purple-600 dark:text-purple-400" />
            </div>
            {p.unmeasurable_parts.length > 0 && (
              <p className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                Ngân hàng đề hiện đo được {Math.round(p.coverage * 100)}% đề thi thật ({p.measured_parts.join(", ") || "chưa có Part nào"} đã có bài làm).{" "}
                {p.unmeasurable_parts.join(", ")} chưa có câu hỏi nên phần điểm này được ngoại suy, vì vậy khoảng dự đoán còn rộng.
              </p>
            )}
            {p.questions_needed_to_narrow && p.questions_needed_to_narrow > 0 ? (
              <div className="flex items-center justify-between gap-3 rounded-lg border border-purple-200/80 bg-purple-50/70 p-2.5 text-[11px] text-purple-900 dark:border-purple-800/60 dark:bg-purple-950/40 dark:text-purple-200">
                <span>
                  Độ tin cậy: <strong className="font-semibold">{p.confidence_level === "low" ? "thấp" : p.confidence_level === "medium" ? "trung bình" : "cao"}</strong> ({Math.round(p.confidence * 100)}%). Cần thêm <strong>{p.questions_needed_to_narrow} câu</strong> ở các Part đã có đề để thu hẹp khoảng dự đoán.
                </span>
                <Link href="/mock-tests?mode=smart" className="shrink-0 font-semibold text-purple-700 underline hover:text-purple-900 dark:text-purple-300">
                  Luyện thông minh ngay →
                </Link>
              </div>
            ) : p.confidence_level === "high" ? (
              <p className="rounded-lg bg-emerald-50 p-2 text-[11px] text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                ✓ Dữ liệu đạt độ tin cậy cao ({Math.round(p.confidence * 100)}% • {data.total_attempts} câu đã làm).
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card className={cn(CARD, "lg:col-span-5")}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
              <Clock className="h-5 w-5 text-emerald-500" aria-hidden="true" /> Thời gian học 14 ngày
            </CardTitle>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {totalMinutes} phút • {studiedDays}/14 ngày có học • mục tiêu {data.study_minutes[0]?.goal_minutes ?? 0} phút/ngày
            </p>
          </CardHeader>
          <CardContent>
            <div className="flex h-36 items-end gap-1" role="img" aria-label="Biểu đồ phút học mỗi ngày">
              {data.study_minutes.map((day) => (
                <div key={day.date} className="group relative flex h-full flex-1 flex-col justify-end" title={`${formatDate(day.date)}: ${day.minutes} phút ${Object.entries(day.by_kind).map(([k, v]) => `• ${KIND_LABELS[k] ?? k} ${Math.round(v)}'`).join(" ")}`}>
                  <div className="absolute w-full border-t border-dashed border-emerald-400/60" style={{ bottom: `${(day.goal_minutes / maxMinutes) * 100}%` }} />
                  <div
                    className={cn("w-full rounded-t", day.minutes >= day.goal_minutes ? "bg-emerald-500" : day.minutes > 0 ? "bg-emerald-300 dark:bg-emerald-600/70" : "bg-slate-200 dark:bg-slate-700")}
                    style={{ height: `${Math.max(2, (day.minutes / maxMinutes) * 100)}%` }}
                  />
                </div>
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-slate-500">
              <span>{formatDate(data.study_minutes[0]?.date)}</span>
              <span>Hôm nay</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className={CARD}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
            <Brain className="h-5 w-5 text-blue-500" aria-hidden="true" /> Mức thành thạo 12 chuyên đề cú pháp
          </CardTitle>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">Thanh mờ = chưa luyện (đang dùng ước lượng từ điểm đầu vào). Kế hoạch tuần ưu tiên chuyên đề thấp nhất.</p>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-x-6 gap-y-3 md:grid-cols-2">
            {lessons.map((stat) => (
              <li key={stat.key} className="space-y-1">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <Link href={`/lessons?lesson=${stat.lesson_number}`} className="truncate font-semibold text-slate-800 hover:underline dark:text-slate-200">{stat.label}</Link>
                  <span className="flex shrink-0 items-center gap-1.5">
                    <Trend value={stat.trend} />
                    <span className={cn("rounded-full border px-1.5 text-[10px] font-semibold", LESSON_STATUS[stat.status].style)}>{LESSON_STATUS[stat.status].label}</span>
                    <span className="w-9 text-right font-mono font-bold">{stat.attempts ? percent(stat.mastery) : "—"}</span>
                  </span>
                </div>
                <MasteryBar stat={stat} />
                <p className="text-[10px] text-slate-500">
                  {stat.attempts} lượt • {stat.distinct_questions}/{stat.question_count} câu đã làm
                  {stat.open_errors ? ` • ${stat.open_errors} lỗi mở` : ""}
                  {stat.avg_time_seconds ? ` • ${Math.round(stat.avg_time_seconds)}s/câu` : ""}
                </p>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className={CARD}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
              <Gauge className="h-5 w-5 text-amber-500" aria-hidden="true" /> Theo Part & tốc độ làm bài
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] text-slate-500 uppercase">
                <tr><th className="p-1.5">Part</th><th className="p-1.5">Mastery</th><th className="p-1.5 text-center">Lượt</th><th className="p-1.5 text-center">Tốc độ / mục tiêu</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {parts.map((stat) => {
                  const slow = stat.avg_time_seconds && stat.target_seconds && stat.avg_time_seconds > stat.target_seconds * 1.3;
                  return (
                    <tr key={stat.key}>
                      <td className="p-1.5 font-semibold">{stat.part}</td>
                      <td className="w-1/3 p-1.5"><MasteryBar stat={stat} /></td>
                      <td className="p-1.5 text-center">{stat.attempts}</td>
                      <td className={cn("p-1.5 text-center font-mono", slow ? "font-bold text-amber-600" : "")}>
                        {stat.avg_time_seconds ? `${Math.round(stat.avg_time_seconds)}s` : "—"} / {stat.target_seconds}s
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {data.pace.some((row) => row.slow) && (
              <Link href="/mock-tests?mode=exam&part=Part%205" className="mt-3 block text-xs font-semibold text-amber-700 hover:underline dark:text-amber-300">
                ⏱️ Bạn đang chậm ở {data.pace.filter((r) => r.slow).map((r) => r.part).join(", ")} — luyện chế độ thi thật bấm giờ →
              </Link>
            )}
          </CardContent>
        </Card>

        <Card className={CARD}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
              <Layers className="h-5 w-5 text-blue-500" aria-hidden="true" /> Chất lượng ghi nhớ từ vựng
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <p>
              Tỉ lệ nhớ 30 ngày:{" "}
              <strong className="text-lg">{data.srs_retention.rate === null ? "—" : percent(data.srs_retention.rate)}</strong>{" "}
              <span className="text-slate-500">({data.srs_retention.retained}/{data.srs_retention.reviews} lượt ôn thẻ cũ)</span>
            </p>
            <p className="text-[11px] text-slate-500">Mức lý tưởng 80-90%. Thấp hơn → giảm thẻ mới/ngày; cao hơn → có thể tăng tốc.</p>
            {data.leech_cards.length > 0 ? (
              <div className="space-y-2">
                <p className="font-semibold text-slate-800 dark:text-slate-200">Thẻ hay quên (≥ 3 lần &quot;Again&quot;)</p>
                <ul className="flex flex-wrap gap-1.5">
                  {data.leech_cards.map((card) => (
                    <li key={card.card_id} className="rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
                      {card.word} ×{card.lapses}
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  variant="outline"
                  className="cursor-pointer"
                  onClick={() => askMentor(`Các thẻ tôi hay quên: ${data.leech_cards.map((c) => c.word).join(", ")}. Hãy sửa từng thẻ với câu ví dụ mới dễ nhớ hơn, collocation và mẹo nhớ ngắn.`, { pageContext: "/analytics" })}
                >
                  <Sparkles className="h-3.5 w-3.5 text-purple-500" aria-hidden="true" /> Nhờ AI làm các thẻ này dễ nhớ hơn
                </Button>
              </div>
            ) : (
              <p className="text-slate-500">Chưa có thẻ nào bị quên lặp lại.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
