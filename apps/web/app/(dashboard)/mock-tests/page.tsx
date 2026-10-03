"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Brain, Clock, FileText, History, Play, RotateCcw, Sparkles, Timer, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { QuizSession, timeLimitFor } from "@/modules/mock-tests/components/quiz-session";
import { formatDate, formatDuration, percent } from "@/lib/format";
import { refreshLearner, useLearnerStore } from "@/lib/learner-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { MockTestItem, PracticeMode, PracticeQuestion, Submission } from "@/types";

type PageMode = "smart" | "review" | "exam" | "practice";

const MODE_LABELS: Record<string, string> = { practice: "Luyện", study: "Học & giải", exam: "Thi thật", review: "Ôn lỗi", smart: "Thông minh" };

function ModeCard({ active, onClick, icon: Icon, title, hint, badge }: {
  active: boolean;
  onClick: () => void;
  icon: typeof Brain;
  title: string;
  hint: string;
  badge?: string | null;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex cursor-pointer flex-col gap-1 rounded-xl border p-4 text-left transition",
        active ? "border-blue-500 bg-blue-50 shadow-sm dark:bg-blue-600/15" : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800/80",
      )}
    >
      <span className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <Icon className="h-4 w-4 text-blue-500" aria-hidden="true" /> {title}
        </span>
        {badge && <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700 dark:bg-red-500/20 dark:text-red-300">{badge}</span>}
      </span>
      <span className="text-[11px] text-slate-500 dark:text-slate-400">{hint}</span>
    </button>
  );
}

function MockTestsContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const stats = useLearnerStore((state) => state.stats);
  const lessonParam = Number(searchParams.get("lesson"));
  const lesson = Number.isInteger(lessonParam) && lessonParam >= 1 && lessonParam <= 12 ? lessonParam : null;
  const rawMode = searchParams.get("mode");
  const pageMode: PageMode = rawMode === "smart" || rawMode === "review" || rawMode === "exam" ? rawMode : "practice";
  const partParam = searchParams.get("part");

  const tests = useApi<MockTestItem[]>("/tests");
  const history = useApi<Submission[]>("/tests/submissions?limit=10");
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [session, setSession] = useState(0);

  const test = tests.data?.find((t) => t.test_id === selectedTest) ?? tests.data?.find((t) => t.test_id === "ETS2024_01") ?? tests.data?.[0] ?? null;
  const partNames = test ? Object.keys(test.parts) : [];
  const part = lesson ? null : partParam && partNames.includes(partParam) ? partParam : partNames.includes("Part 5") ? "Part 5" : (partNames[0] ?? null);

  let questionsPath: string | null = null;
  if (pageMode === "smart") questionsPath = "/practice/smart?count=15";
  else if (pageMode === "review") questionsPath = "/practice/review-queue?limit=30";
  else if (lesson) {
    questionsPath = `/knowledge/lessons/${lesson}/drill`;
  } else if (test) {
    questionsPath = `/tests/${encodeURIComponent(test.test_id)}/questions${part ? `?part=${encodeURIComponent(part)}` : ""}`;
  }
  const questions = useApi<PracticeQuestion[]>(questionsPath);

  const setMode = (mode: PageMode) => {
    setSession(0);
    const params = new URLSearchParams();
    if (mode !== "practice") params.set("mode", mode);
    if (mode === "exam") params.set("part", part ?? "Part 5");
    router.replace(`${pathname}${params.size ? `?${params.toString()}` : ""}`, { scroll: false });
  };
  const setPart = (name: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("part", name);
    params.delete("lesson");
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const onSubmitted = () => {
    history.reload();
    void refreshLearner();
  };

  if (tests.error) return <ErrorState message={tests.error} onRetry={tests.reload} />;
  if (tests.loading || !tests.data) return <LoadingState label="Đang tải ngân hàng đề..." />;

  const list: PracticeQuestion[] = questions.data ?? [];
  const limit = list.length ? timeLimitFor(list) : 0;
  const quizMode: PracticeMode = pageMode === "practice" ? "practice" : pageMode;
  const title =
    pageMode === "smart" ? "Luyện thông minh (cá nhân hoá)"
      : pageMode === "review" ? "Ôn câu sai đến hạn"
        : pageMode === "exam" ? `Thi thật bấm giờ • ${part ?? ""}`
          : lesson ? `Luyện Phản Xạ Chuyên Đề: Bài ${String(lesson).padStart(2, "0")}` : `${test?.name ?? ""} • ${part ?? ""}`;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Luyện Thi Thực Chiến</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Mỗi câu được ghi lại (đúng/sai, thời gian) để cập nhật mức thành thạo, lịch ôn lỗi và kế hoạch của bạn.
          </p>
        </div>
        {session > 0 && (
          <Button variant="outline" onClick={() => setSession(0)} className="self-start sm:self-auto cursor-pointer">
            Thoát phòng thi
          </Button>
        )}
      </div>

      {session > 0 ? (
        <QuizSession
          key={session}
          questions={list}
          mode={quizMode}
          title={title}
          part={part}
          lessonNumber={lesson}
          onSubmitted={onSubmitted}
          onRestart={() => setSession((s) => s + 1)}
        />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ModeCard active={pageMode === "smart"} onClick={() => setMode("smart")} icon={Brain} title="Luyện thông minh"
              hint="Trộn câu sai đến hạn, chuyên đề yếu nhất và câu chưa làm" />
            <ModeCard active={pageMode === "review"} onClick={() => setMode("review")} icon={RotateCcw} title="Ôn câu sai"
              hint="Lịch 1-3-7 ngày: đúng 3 lần là nắm chắc" badge={stats?.error_reviews_due ? `${stats.error_reviews_due} đến hạn` : null} />
            <ModeCard active={pageMode === "exam"} onClick={() => setMode("exam")} icon={Timer} title="Thi thật bấm giờ"
              hint="Không xem đáp án giữa chừng, đo tốc độ từng câu" />
            <ModeCard active={pageMode === "practice"} onClick={() => setMode("practice")} icon={FileText} title="Theo đề / chuyên đề"
              hint="Chọn đề, Part hoặc luyện riêng một chuyên đề" />
          </div>

          <Card className="relative overflow-hidden border-blue-200 bg-gradient-to-r from-blue-50/80 via-white to-white dark:border-blue-500/30 dark:from-blue-950/40 dark:via-slate-900 dark:to-slate-900">
            <CardHeader>
              {!lesson && (pageMode === "practice" || pageMode === "exam") && (
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  {tests.data.map((item) => (
                    <button
                      key={item.test_id}
                      type="button"
                      onClick={() => setSelectedTest(item.test_id)}
                      className={cn(
                        "cursor-pointer rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                        item.test_id === test?.test_id
                          ? "border-blue-300 bg-blue-100 text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/20 dark:text-blue-300"
                          : "border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-400",
                      )}
                    >
                      {item.name} ({item.available_questions})
                    </button>
                  ))}
                </div>
              )}
              <CardTitle className="text-2xl font-bold text-slate-900 dark:text-white">{title}</CardTitle>
              {lesson && pageMode === "practice" ? (
                <p className="mt-1 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                  Bộ câu hỏi rèn phản xạ chuyên sâu độc lập (Nguồn chuẩn Hackers TOEIC & ETS Grammar Drills).
                  <Link href="/mock-tests" className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400">
                    <X className="h-3 w-3" aria-hidden="true" /> Quay lại chọn đề
                  </Link>
                </p>
              ) : (pageMode === "practice" || pageMode === "exam") && (
                <div className="mt-2 flex flex-wrap gap-2" role="radiogroup" aria-label="Chọn Part">
                  {partNames.map((name) => (
                    <button
                      key={name}
                      type="button"
                      role="radio"
                      aria-checked={name === part}
                      onClick={() => setPart(name)}
                      className={cn(
                        "cursor-pointer rounded-lg border px-3 py-1 text-xs font-semibold shrink-0",
                        name === part ? "border-blue-500 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300",
                      )}
                    >
                      {name} ({test?.parts[name]})
                    </button>
                  ))}
                </div>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {questions.error ? (
                <ErrorState message={questions.error} onRetry={questions.reload} />
              ) : questions.loading ? (
                <LoadingState label="Đang chuẩn bị bộ câu..." />
              ) : list.length === 0 ? (
                <EmptyState title={pageMode === "review" ? "Không có câu sai đến hạn hôm nay 🎉" : "Chưa có câu hỏi"}>
                  {pageMode === "review" ? "Câu sai sẽ quay lại đúng lịch 1-3-7 ngày. Hãy thử Luyện thông minh." : "Chọn đề hoặc Part khác."}
                </EmptyState>
              ) : (
                <>
                  <div className="grid max-w-md grid-cols-3 gap-2 sm:gap-4 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                    <span className="flex items-center gap-1.5 sm:gap-2"><FileText className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-blue-500" aria-hidden="true" /> {list.length} câu</span>
                    <span className="flex items-center gap-1.5 sm:gap-2"><Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-amber-500" aria-hidden="true" /> {formatDuration(limit)}</span>
                    <span className="flex items-center gap-1.5 sm:gap-2"><Sparkles className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-purple-500" aria-hidden="true" /> {pageMode === "exam" ? "Bấm giờ" : "Giải 3 chiều"}</span>
                  </div>
                  {pageMode === "smart" && (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                        <span className="font-medium text-slate-500">Độ khó thích ứng:</span>
                        {Object.entries(
                          list.reduce<Record<string, number>>(
                            (acc, q) => {
                              const label = q.difficulty === "easy" ? "Cơ bản" : q.difficulty === "hard" ? "Nâng cao" : "Tiêu chuẩn";
                              return { ...acc, [label]: (acc[label] ?? 0) + 1 };
                            },
                            {}
                          )
                        ).map(([diff, count]) => (
                          <span
                            key={diff}
                            className={cn(
                              "rounded-full border px-2 py-0.5 font-semibold",
                              diff === "Cơ bản"
                                ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
                                : diff === "Nâng cao"
                                  ? "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300"
                                  : "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300"
                            )}
                          >
                            {count} × {diff}
                          </span>
                        ))}
                      </div>
                      <ul className="flex flex-wrap gap-1.5 text-[11px]">
                        {Object.entries(list.reduce<Record<string, number>>((acc, q) => ({ ...acc, [q.reason ?? "Khác"]: (acc[q.reason ?? "Khác"] ?? 0) + 1 }), {})).map(([reason, count]) => (
                          <li key={reason} className="rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-purple-700 dark:border-purple-500/30 dark:bg-purple-500/10 dark:text-purple-300">
                            {count} × {reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="pt-2 pb-4 sm:pb-0">
                    <Button size="lg" onClick={() => setSession(1)} className="flex cursor-pointer items-center justify-center gap-2 bg-blue-600 px-8 w-full sm:w-auto font-semibold text-white hover:bg-blue-500">
                      <Play className="h-4 w-4 fill-white" aria-hidden="true" /> Bắt đầu bài luyện
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
            <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
              <CardTitle className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                <History className="h-4 w-4 text-blue-500" aria-hidden="true" /> Lịch sử bài luyện
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-3">
              {history.error ? (
                <ErrorState message={history.error} onRetry={history.reload} />
              ) : !history.data?.length ? (
                <p className="py-4 text-center text-xs text-slate-500">Chưa có bài nộp nào. Kết quả sẽ hiện ở đây, trên Dashboard và trong Phân tích.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-[11px] text-slate-500 uppercase">
                      <tr>
                        <th className="p-2">Thời gian</th>
                        <th className="p-2">Chế độ</th>
                        <th className="p-2">Nội dung</th>
                        <th className="p-2 text-center">Đúng</th>
                        <th className="p-2 text-center">Tỉ lệ</th>
                        <th className="p-2 text-center">Thời lượng</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                      {history.data.map((sub) => (
                        <tr key={sub.id}>
                          <td className="p-2 whitespace-nowrap">{formatDate(sub.submitted_at, true)}</td>
                          <td className="p-2">{MODE_LABELS[sub.mode ?? "practice"] ?? sub.mode}</td>
                          <td className="p-2">{sub.lesson_number ? `Bài ${String(sub.lesson_number).padStart(2, "0")}` : sub.part}</td>
                          <td className="p-2 text-center font-mono">{sub.correct_count}/{sub.total_questions}</td>
                          <td className="p-2 text-center font-semibold">{percent(sub.accuracy)}</td>
                          <td className="p-2 text-center font-mono">{formatDuration(sub.time_spent_seconds ?? 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function MockTestsPage() {
  return (
    <Suspense fallback={<LoadingState label="Đang tải phòng thi..." />}>
      <MockTestsContent />
    </Suspense>
  );
}
