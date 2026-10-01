"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Calculator, CheckCircle2, History, Target, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { ErrorState } from "@/components/states";
import { SkillInsights } from "@/components/insights/skill-insights";
import { WeeklyReportCard } from "@/components/insights/weekly-report";
import { api, errorMessage } from "@/lib/api";
import { ERROR_TYPES, formatDate, lessonHref, percent } from "@/lib/format";
import { useLearnerStore } from "@/lib/learner-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { ScoreCalcResult, Submission } from "@/types";

const LISTENING_PARTS = new Set(["Part 1", "Part 2", "Part 3", "Part 4"]);
const CARD = "border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80";

function RawSlider({ id, label, value, onChange, tone }: { id: string; label: string; value: number; onChange: (v: number) => void; tone: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <Label id={id}>{label}</Label>
        <span className={cn("text-base font-bold", tone)}>{value} / 100</span>
      </div>
      <Slider aria-labelledby={id} value={[value]} max={100} step={1} onValueChange={(v) => onChange(Array.isArray(v) ? v[0] : v)} className="py-2" />
    </div>
  );
}

export default function AnalyticsPage() {
  const stats = useLearnerStore((state) => state.stats);
  const submissions = useApi<Submission[]>("/tests/submissions?limit=20");
  const [listening, setListening] = useState(75);
  const [reading, setReading] = useState(70);
  const [targetDraft, setTargetDraft] = useState<number | null>(null);
  const [result, setResult] = useState<ScoreCalcResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const target = targetDraft ?? stats?.target_score ?? 800;

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      api<ScoreCalcResult>(`/tests/calculate-score?target=${Math.min(990, Math.max(10, target))}`, {
        method: "POST",
        json: { raw_listening: listening, raw_reading: reading },
      }).then(
        (data) => {
          if (!cancelled) {
            setResult(data);
            setError(null);
          }
        },
        (err: unknown) => !cancelled && setError(errorMessage(err)),
      );
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [listening, reading, target]);

  const history = submissions.data ?? [];
  const latestReading = history.find((s) => s.accuracy != null && s.part && !LISTENING_PARTS.has(s.part) && s.part !== "Mixed");
  const latestListening = history.find((s) => s.accuracy != null && s.part && LISTENING_PARTS.has(s.part));
  const rca = stats?.rca_breakdown ?? {};
  const rcaMax = Math.max(1, ...Object.values(rca));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Phân Tích Quá Trình Học</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Hồ sơ năng lực được tính từ từng câu bạn làm, thời gian học và lịch sử ôn thẻ — đây là dữ liệu mà kế hoạch và AI Mentor dùng để cá nhân hoá.
        </p>
      </div>

      <WeeklyReportCard />

      <SkillInsights />

      <h2 className="pt-2 text-xl font-bold text-slate-900 dark:text-white">Bảng quy đổi điểm thô (ETS curve)</h2>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-6">
          <Card className={CARD}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white">
                <Calculator className="h-5 w-5 text-blue-500" aria-hidden="true" /> Quy đổi điểm thô
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <RawSlider id="raw-listening" label="Listening (số câu đúng / 100)" value={listening} onChange={setListening} tone="text-blue-600 dark:text-blue-400" />
              <RawSlider id="raw-reading" label="Reading (số câu đúng / 100)" value={reading} onChange={setReading} tone="text-purple-600 dark:text-purple-400" />
              <div className="space-y-1">
                <Label htmlFor="target">Mục tiêu (mặc định lấy từ hồ sơ)</Label>
                <Input id="target" type="number" min={10} max={990} step={5} value={target} onChange={(e) => setTargetDraft(Number(e.target.value) || null)} />
              </div>
              {(latestReading || latestListening) && (
                <div className="flex flex-wrap gap-2">
                  {latestReading && (
                    <Button size="sm" variant="outline" className="cursor-pointer text-xs" onClick={() => setReading(Math.round((latestReading.accuracy ?? 0) * 100))}>
                      Reading theo bài gần nhất ({percent(latestReading.accuracy)})
                    </Button>
                  )}
                  {latestListening && (
                    <Button size="sm" variant="outline" className="cursor-pointer text-xs" onClick={() => setListening(Math.round((latestListening.accuracy ?? 0) * 100))}>
                      Listening theo bài gần nhất ({percent(latestListening.accuracy)})
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className={CARD}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white">
                <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden="true" /> Lỗi của bạn theo 5 RCA
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {ERROR_TYPES.map((t) => {
                const count = rca[t.key] ?? 0;
                return (
                  <Link key={t.key} href={`/error-log?type=${t.key}`} className="block space-y-1 rounded-lg p-1 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <div className="flex justify-between">
                      <span className="text-slate-700 dark:text-slate-300">
                        <strong className={cn("font-mono", t.color)}>[{t.key}]</strong> {t.label}
                      </span>
                      <span className="font-mono font-bold">{count}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900">
                      <div className={cn("h-1.5 rounded-full", t.bar)} style={{ width: `${count ? Math.max(4, (count / rcaMax) * 100) : 0}%` }} />
                    </div>
                  </Link>
                );
              })}
              {stats?.learning_gaps.length ? (
                <div className="space-y-1.5 border-t border-slate-100 pt-3 dark:border-slate-700/60">
                  <p className="font-semibold text-slate-800 dark:text-slate-200">Lỗ hổng lớn nhất</p>
                  {stats.learning_gaps.slice(0, 3).map((gap) => (
                    <p key={gap.id} className="flex justify-between gap-2 text-slate-600 dark:text-slate-400">
                      <span>
                        {gap.topic} ({gap.error_count})
                      </span>
                      {gap.lesson_number && (
                        <Link href={lessonHref(gap.lesson_number)} className="font-semibold text-blue-600 dark:text-blue-400">
                          Bài {String(gap.lesson_number).padStart(2, "0")} →
                        </Link>
                      )}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500">Chưa có dữ liệu lỗi — hãy làm một bài luyện.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6 lg:col-span-6">
          {error && <ErrorState message={error} />}
          {result && (
            <Card className="border-blue-200 bg-gradient-to-b from-blue-50/60 to-white dark:border-blue-500/30 dark:from-slate-800 dark:to-slate-900">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-sm font-semibold text-slate-500 uppercase">Điểm thang 990 dự kiến</CardTitle>
                <div className="mt-2 text-6xl font-black tracking-tight text-slate-900 dark:text-white" aria-live="polite">
                  {result.total_score}
                  <span className="text-2xl font-bold text-slate-400"> / 990</span>
                </div>
                <span className="mx-auto mt-2 rounded-full border border-blue-200 bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/20 dark:text-blue-300">
                  {result.cefr_level}
                </span>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{result.cefr_description}</p>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
                    <span className="text-xs text-slate-500">Listening</span>
                    <p className="mt-1 text-3xl font-extrabold text-blue-600 dark:text-blue-400">{result.scaled_listening}</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
                    <span className="text-xs text-slate-500">Reading</span>
                    <p className="mt-1 text-3xl font-extrabold text-purple-600 dark:text-purple-400">{result.scaled_reading}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
                  <div className="flex items-center gap-2">
                    <Target className="h-5 w-5 text-amber-500" aria-hidden="true" />
                    <div>
                      <p className="text-xs text-slate-500">Mục tiêu {result.target_score}+</p>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">
                        {result.target_gap > 0
                          ? `Còn thiếu ${result.target_gap} điểm ≈ +${result.suggested_gain_listening} câu Listening, +${result.suggested_gain_reading} câu Reading`
                          : "Đã đạt mục tiêu! 🎉"}
                      </p>
                    </div>
                  </div>
                  <TrendingUp className="h-5 w-5 text-emerald-500" aria-hidden="true" />
                </div>
              </CardContent>
            </Card>
          )}

          {result && (
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700/70 dark:bg-slate-800/80">
              <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" /> Khuyến nghị theo điểm số
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                {result.recommendations.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </div>
          )}

          <Card className={CARD}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                <History className="h-4 w-4 text-blue-500" aria-hidden="true" /> Xu hướng bài luyện
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!history.length ? (
                <p className="text-xs text-slate-500">
                  Chưa có bài nộp. <Link href="/mock-tests" className="font-semibold text-blue-600 dark:text-blue-400">Làm bài đầu tiên</Link>.
                </p>
              ) : (
                <div className="space-y-2">
                  {history
                    .slice(0, 10)
                    .reverse()
                    .map((sub) => (
                      <div key={sub.id} className="flex items-center gap-3 text-xs">
                        <span className="w-20 shrink-0 text-slate-500">{formatDate(sub.submitted_at, true)}</span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900">
                          <div
                            className={cn("h-2 rounded-full", (sub.accuracy ?? 0) >= 0.8 ? "bg-emerald-500" : (sub.accuracy ?? 0) >= 0.6 ? "bg-amber-500" : "bg-red-500")}
                            style={{ width: `${Math.round((sub.accuracy ?? 0) * 100)}%` }}
                          />
                        </div>
                        <span className="w-24 shrink-0 text-right font-mono">
                          {percent(sub.accuracy)} • {sub.lesson_number ? `B${sub.lesson_number}` : sub.part}
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
