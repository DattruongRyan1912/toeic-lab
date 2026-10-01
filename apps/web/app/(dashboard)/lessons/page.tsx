"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, BookOpen, Bot, ChevronRight, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Markdown } from "@/components/markdown";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { LessonMastery, LessonStudy } from "@/components/lessons/lesson-study";
import { LESSON_STATUS, percent } from "@/lib/format";
import { askMentor } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { Lesson, LessonDetail } from "@/types";

function LessonDetailPanel({ number }: { number: number }) {
  const detail = useApi<LessonDetail>(`/knowledge/lessons/${number}`);
  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return <LoadingState label="Đang tải bài học..." />;
  const lesson = detail.data;
  const stats = lesson.stats;

  return (
    <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-4 dark:border-slate-700/60">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-xl font-bold text-slate-900 dark:text-white">{lesson.title}</CardTitle>
            {lesson.subtitle && <p className="mt-0.5 font-mono text-xs text-blue-600 dark:text-blue-400">{lesson.subtitle}</p>}
          </div>
          <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-semibold", LESSON_STATUS[stats.status].style)}>
            {LESSON_STATUS[stats.status].label}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-center text-xs">
          <div className="rounded-lg border border-slate-200 p-2 dark:border-slate-700">
            <p className="text-slate-500">Độ chính xác</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{percent(stats.accuracy)}</p>
            <p className="text-[10px] text-slate-500">
              {stats.correct}/{stats.answered} câu đã làm
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 p-2 dark:border-slate-700">
            <p className="text-slate-500">Câu luyện</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{stats.question_count}</p>
            <p className="text-[10px] text-slate-500">trong ngân hàng đề</p>
          </div>
          <Link href="/error-log" className="rounded-lg border border-slate-200 p-2 hover:border-red-300 dark:border-slate-700">
            <p className="text-slate-500">Lỗi chưa khắc phục</p>
            <p className={cn("text-lg font-bold", stats.open_errors ? "text-red-500" : "text-slate-900 dark:text-white")}>{stats.open_errors}</p>
            <p className="text-[10px] text-slate-500">trong Sổ lỗi</p>
          </Link>
        </div>
        <LessonMastery lesson={lesson} />
      </CardHeader>
      <CardContent className="space-y-6 pt-5">
        {lesson.syntax_formula && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10">
            <p className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 uppercase dark:text-emerald-400">
              <Sparkles className="h-4 w-4" aria-hidden="true" /> Công thức cốt lõi
            </p>
            <p className="mt-1 font-mono text-sm text-slate-800 dark:text-slate-200">{lesson.syntax_formula}</p>
          </div>
        )}
        {lesson.summary && <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">{lesson.summary}</p>}

        {lesson.content_md ? (
          <Markdown className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">{lesson.content_md}</Markdown>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 p-4 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            Chưa có nội dung chi tiết cho bài này (thêm file <code>lessons/bai_{String(number).padStart(2, "0")}_*.md</code> rồi chạy lại seed). Bạn vẫn có thể luyện câu hỏi liên quan hoặc nhờ AI Mentor giảng bài.
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {stats.question_count > 0 && (
            <Link href={`/mock-tests?lesson=${number}`}>
              <Button className="flex cursor-pointer items-center gap-2 bg-blue-600 text-white hover:bg-blue-500">
                <Play className="h-4 w-4 fill-white" aria-hidden="true" /> Luyện {stats.question_count} câu của chuyên đề
              </Button>
            </Link>
          )}
          <Button
            variant="outline"
            className="flex cursor-pointer items-center gap-2"
            onClick={() =>
              askMentor(`Giảng lại ${lesson.title} theo cách của kỹ sư phần mềm: quy tắc nhận diện trong 10 giây, 3 bẫy ETS hay gặp và 3 câu luyện có đáp án.`, {
                pageContext: `/lessons?lesson=${number}`,
              })
            }
          >
            <Bot className="h-4 w-4 text-purple-500" aria-hidden="true" /> Nhờ AI Mentor giảng
          </Button>
        </div>

        <LessonStudy key={lesson.lesson_number} lesson={lesson} onChanged={detail.reload} />

        {lesson.questions.length > 0 && (
          <div className="space-y-3">
            <h3 className="flex items-center gap-1.5 text-xs font-bold text-purple-700 uppercase dark:text-purple-400">
              <BookOpen className="h-4 w-4" aria-hidden="true" /> Câu hỏi thuộc chuyên đề ({lesson.questions.length})
            </h3>
            {lesson.questions.slice(0, 6).map((q) => (
              <details key={q.id} className="group rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <summary className="cursor-pointer list-none text-sm font-semibold text-slate-800 dark:text-slate-200">
                  <span className="mr-2 font-mono text-xs text-slate-500">Câu {q.question_no}</span>
                  {q.sentence}
                </summary>
                <div className="mt-3 space-y-2 text-xs text-slate-600 dark:text-slate-400">
                  <p>
                    (A) {q.choice_a} • (B) {q.choice_b} • (C) {q.choice_c}
                    {q.choice_d ? ` • (D) ${q.choice_d}` : ""}
                  </p>
                  <p className="font-semibold text-emerald-600 dark:text-emerald-400">Đáp án: ({q.correct_choice})</p>
                  {q.explanation && <p>💡 {q.explanation}</p>}
                  {q.distractor_analysis && <p className="text-amber-700 dark:text-amber-300">⚠️ {q.distractor_analysis}</p>}
                </div>
              </details>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function LessonsContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const lessons = useApi<Lesson[]>("/knowledge/lessons");

  if (lessons.error) return <ErrorState message={lessons.error} onRetry={lessons.reload} />;
  if (!lessons.data) return <LoadingState label="Đang tải 12 chuyên đề..." />;
  if (!lessons.data.length) {
    return (
      <EmptyState title="Chưa có bài học trong database">
        Chạy <code>python scripts/seed_database.py</code>.
      </EmptyState>
    );
  }

  const requested = Number(searchParams.get("lesson"));
  const selected = lessons.data.find((l) => l.lesson_number === requested)?.lesson_number ?? lessons.data[0].lesson_number;
  const practiced = lessons.data.filter((l) => l.stats.answered > 0).length;
  const strong = lessons.data.filter((l) => l.stats.status === "strong").length;
  const select = (number: number) => router.replace(`${pathname}?lesson=${number}`, { scroll: false });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50/80 via-white to-indigo-50/60 p-6 md:p-8 dark:border-blue-500/20 dark:from-blue-950/60 dark:via-slate-900 dark:to-indigo-950/50">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <span className="rounded-full border border-blue-200 bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/20 dark:text-blue-400">
              SYNTAX RULES • PART 5
            </span>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">12 Chuyên Đề Cú Pháp Giải Nhanh Part 5</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-400">
              Mỗi câu trong ngân hàng đề được gắn vào một chuyên đề theo tag bẫy — độ chính xác và lỗi của bạn được tính riêng cho từng bài.
            </p>
          </div>
          <div className="shrink-0 rounded-xl border border-slate-200 bg-white p-4 text-center dark:border-slate-800 dark:bg-slate-900/80">
            <span className="block text-xs font-semibold text-slate-500 uppercase">Đã luyện / Vững</span>
            <span className="text-2xl font-black text-blue-600 dark:text-blue-400">
              {practiced} / {strong}
            </span>
            <span className="block text-[11px] text-slate-500">trên {lessons.data.length} chuyên đề</span>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <nav className="space-y-2.5 lg:col-span-5" aria-label="Danh sách chuyên đề">
          {lessons.data.map((lesson) => {
            const active = lesson.lesson_number === selected;
            const status = LESSON_STATUS[lesson.stats.status];
            return (
              <button
                key={lesson.id}
                type="button"
                onClick={() => select(lesson.lesson_number)}
                aria-current={active ? "true" : undefined}
                className={cn(
                  "flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl border p-4 text-left transition",
                  active
                    ? "border-blue-500 bg-blue-50 shadow-lg shadow-blue-500/10 dark:bg-blue-600/15"
                    : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800/80 dark:bg-slate-900/60 dark:hover:border-slate-700",
                )}
              >
                <div className="min-w-0">
                  <p className="text-sm leading-snug font-bold text-slate-900 dark:text-white">{lesson.title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px]">
                    <span className={cn("rounded-full border px-1.5 py-0.5 font-semibold", status.style)}>{status.label}</span>
                    {lesson.stats.answered > 0 && <span className="text-slate-500">{percent(lesson.stats.accuracy)} đúng</span>}
                    {lesson.stats.open_errors > 0 && (
                      <span className="flex items-center gap-0.5 font-semibold text-red-500">
                        <AlertCircle className="h-3 w-3" aria-hidden="true" /> {lesson.stats.open_errors} lỗi
                      </span>
                    )}
                    {lesson.stats.question_count > 0 && <span className="text-slate-500">• {lesson.stats.question_count} câu</span>}
                    {lesson.has_full_content && <span className="text-emerald-600 dark:text-emerald-400">• Có bài giảng</span>}
                  </div>
                </div>
                <ChevronRight className={cn("h-4 w-4 shrink-0", active ? "text-blue-500" : "text-slate-400")} aria-hidden="true" />
              </button>
            );
          })}
        </nav>
        <div className="lg:col-span-7">
          <LessonDetailPanel key={selected} number={selected} />
        </div>
      </div>
    </div>
  );
}

export default function LessonsPage() {
  return (
    <Suspense fallback={<LoadingState label="Đang tải 12 chuyên đề..." />}>
      <LessonsContent />
    </Suspense>
  );
}
