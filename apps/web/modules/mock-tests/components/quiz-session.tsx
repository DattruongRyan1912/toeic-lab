"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import confetti from "canvas-confetti";
import { AlertTriangle, ArrowRight, Bot, Check, CheckCircle2, Clock, Lightbulb, Loader2, RotateCcw, Timer, Volume2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { toast } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { speak } from "@/lib/audio";
import { formatDuration, lessonHref, percent } from "@/lib/format";
import { askMentor } from "@/lib/mentor-store";
import { cn } from "@/lib/utils";
import type { PracticeMode, PracticeQuestion, QuestionResult, QuizSubmitResult } from "@/types";

const LISTENING = new Set(["Part 1", "Part 2", "Part 3", "Part 4"]);
const SECONDS_PER_QUESTION: Record<string, number> = { "Part 2": 25, "Part 5": 30, "Part 6": 40, "Part 7": 60 };
const TARGET_SECONDS: Record<string, number> = { "Part 2": 20, "Part 5": 22, "Part 6": 30, "Part 7": 55 };
const OUTCOME_LABELS: Record<string, { label: string; style: string }> = {
  advanced: { label: "Ôn đúng hạn ✓ tiến 1 bậc", style: "text-emerald-600 dark:text-emerald-400" },
  mastered: { label: "Đã nắm chắc 🎉", style: "text-emerald-600 dark:text-emerald-400" },
  reset: { label: "Sai lại — ôn lại từ ngày mai", style: "text-red-500" },
  early: { label: "Đúng (chưa đến hạn ôn)", style: "text-slate-500" },
};

export function timeLimitFor(questions: PracticeQuestion[]): number {
  return Math.max(60, questions.reduce((sum, q) => sum + (SECONDS_PER_QUESTION[q.part] ?? 30), 0));
}

interface QuizSessionProps {
  questions: PracticeQuestion[];
  mode: PracticeMode;
  title: string;
  part: string | null;
  lessonNumber: number | null;
  onSubmitted: (result: QuizSubmitResult) => void;
  onRestart: () => void;
}

function choicesOf(q: PracticeQuestion) {
  return [
    { key: "A", text: q.choice_a },
    { key: "B", text: q.choice_b },
    { key: "C", text: q.choice_c },
    { key: "D", text: q.choice_d },
  ].filter((c): c is { key: string; text: string } => Boolean(c.text));
}

function askAboutQuestion(q: PracticeQuestion, userChoice: string | null | undefined) {
  const prompt =
    userChoice && userChoice !== q.correct_choice
      ? `Tôi chọn (${userChoice}) ở câu ${q.question_no} nhưng đáp án là (${q.correct_choice}). Phân tích giúp tôi vì sao sai.`
      : `Phân tích câu ${q.question_no} (${q.part}) giúp tôi.`;
  askMentor(prompt, { questionId: q.id, pageContext: "/mock-tests" });
}

function ResultScreen({ result, questions, onRestart }: { result: QuizSubmitResult; questions: PracticeQuestion[]; onRestart: () => void }) {
  const byId = new Map(questions.map((q) => [q.id, q]));
  const wrong = result.results.filter((r) => !r.is_correct);
  const part5 = result.results.filter((r) => r.part === "Part 5" && r.time_ms && r.user_choice);
  const target = TARGET_SECONDS[questions[0]?.part ?? "Part 5"] ?? 25;
  const slow = result.avg_time_seconds != null && result.avg_time_seconds > target * 1.3;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card className="border-slate-200 bg-white p-8 text-center dark:border-slate-700/70 dark:bg-slate-800/80">
        <CardHeader>
          <div className="mx-auto mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
            <Check className="h-8 w-8" aria-hidden="true" />
          </div>
          <CardTitle className="text-3xl font-bold text-slate-900 dark:text-white">Kết quả bài luyện</CardTitle>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {result.lesson_number ? `Bài ${String(result.lesson_number).padStart(2, "0")}` : result.part} • {formatDuration(result.time_spent_seconds)}
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-baseline justify-center gap-2">
            <span className="text-6xl font-black text-slate-900 dark:text-white">{result.correct_count}</span>
            <span className="text-2xl font-bold text-slate-400">/ {result.total_questions}</span>
            <span className="ml-2 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-sm font-semibold text-blue-700 dark:border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400">
              {percent(result.accuracy)}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-left sm:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
              <span className="text-xs text-slate-500">Sai / bỏ trống</span>
              <p className="text-xl font-bold text-red-500">
                {result.total_questions - result.correct_count - result.unanswered} / {result.unanswered}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
              <span className="flex items-center gap-1 text-xs text-slate-500"><Timer className="h-3 w-3" aria-hidden="true" /> Tốc độ</span>
              <p className={cn("text-xl font-bold", slow ? "text-amber-600" : "text-emerald-600 dark:text-emerald-400")}>
                {result.avg_time_seconds != null ? `${result.avg_time_seconds}s/câu` : "—"}
              </p>
              <span className="text-[10px] text-slate-500">mục tiêu ≤ {target}s</span>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
              <span className="text-xs text-slate-500">Câu sai đã ôn</span>
              <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{result.reviews_advanced}</p>
              <span className="text-[10px] text-slate-500">{result.errors_mastered} câu nắm chắc</span>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
              <span className="text-xs text-slate-500">Reading ước lượng</span>
              <p className="text-xl font-bold text-purple-600 dark:text-purple-400">{result.scaled_reading ?? result.scaled_listening ?? "—"}</p>
              <span className="text-[10px] text-slate-500">ngoại suy từ bộ câu này</span>
            </div>
          </div>
          {slow && part5.length >= 3 && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
              ⏱️ Bạn đang chậm hơn nhịp thi thật. Thử chế độ <Link href="/mock-tests?mode=exam&part=Part%205" className="font-semibold underline">Thi thật bấm giờ</Link>: nhìn trước/sau chỗ trống để loại trừ trong 10 giây.
            </p>
          )}
          {result.errors_logged > 0 && (
            <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
              ✅ {result.errors_logged} câu sai đã vào <Link href="/error-log" className="font-semibold underline">Sổ lỗi</Link> với lịch ôn 1-3-7 ngày; kế hoạch ngày mai sẽ nhắc bạn ôn lại.
            </p>
          )}
          <div className="flex justify-center gap-3">
            <Button onClick={onRestart} variant="outline" className="cursor-pointer">
              <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" /> Làm lại
            </Button>
            <Link href="/">
              <Button className="cursor-pointer bg-blue-600 text-white hover:bg-blue-500">Về kế hoạch hôm nay</Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {result.results.some((r) => r.review_outcome) && (
        <Card className="border-slate-200 bg-white p-5 dark:border-slate-700/70 dark:bg-slate-800/80">
          <h3 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">Tiến độ ôn câu sai</h3>
          <ul className="space-y-1.5 text-xs">
            {result.results.filter((r) => r.review_outcome).map((r: QuestionResult) => (
              <li key={r.question_id} className="flex justify-between gap-3">
                <span className="text-slate-700 dark:text-slate-300">Câu {r.question_no} ({r.test_id})</span>
                <span className={cn("font-semibold", OUTCOME_LABELS[r.review_outcome ?? "early"]?.style)}>{OUTCOME_LABELS[r.review_outcome ?? "early"]?.label}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {result.learning_gaps.length > 0 && (
        <Card className="border-slate-200 bg-white p-5 dark:border-slate-700/70 dark:bg-slate-800/80">
          <h3 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">Lỗ hổng kiến thức hiện tại</h3>
          <div className="space-y-2">
            {result.learning_gaps.map((gap) => (
              <div key={gap.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-700">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {gap.topic} <span className="font-normal text-slate-500">• {gap.error_count} lỗi</span>
                </span>
                {gap.lesson_number && (
                  <Link href={lessonHref(gap.lesson_number)} className="font-semibold text-blue-600 hover:underline dark:text-blue-400">
                    Ôn {gap.lesson_title ?? `Bài ${gap.lesson_number}`} →
                  </Link>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {wrong.length > 0 && (
        <Card className="border-slate-200 bg-white p-5 dark:border-slate-700/70 dark:bg-slate-800/80">
          <h3 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">Chữa {wrong.length} câu sai</h3>
          <div className="space-y-3">
            {wrong.map((r) => {
              const q = byId.get(r.question_id);
              if (!q) return null;
              return (
                <div key={r.question_id} className="space-y-2 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-bold text-slate-900 dark:text-white">Câu {r.question_no}</span>
                    <span className="rounded border border-red-200 bg-red-50 px-1.5 font-mono font-bold text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">[{r.error_type}]</span>
                    {r.trap_tag && <span className="text-slate-500">{r.trap_tag}</span>}
                    {r.time_ms ? <span className="text-slate-500">• {Math.round(r.time_ms / 1000)}s</span> : null}
                  </div>
                  <p className="text-sm text-slate-800 dark:text-slate-200">{q.sentence}</p>
                  <p className="text-xs">
                    <span className="font-bold text-red-500 line-through">{r.user_choice ?? "Bỏ trống"}</span> ➔{" "}
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                      ({r.correct_choice}) {choicesOf(q).find((c) => c.key === r.correct_choice)?.text}
                    </span>
                  </p>
                  {q.explanation && <p className="text-xs text-slate-600 dark:text-slate-400">💡 {q.explanation}</p>}
                  <div className="flex flex-wrap gap-3 text-[11px] font-semibold">
                    {r.lesson_number && (
                      <Link href={lessonHref(r.lesson_number)} className="text-blue-600 hover:underline dark:text-blue-400">
                        Ôn Bài {String(r.lesson_number).padStart(2, "0")}
                      </Link>
                    )}
                    <button type="button" className="cursor-pointer text-purple-600 hover:underline dark:text-purple-400" onClick={() => askAboutQuestion(q, r.user_choice)}>
                      Hỏi AI Mentor về câu này
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

export function QuizSession({ questions, mode, title, part, lessonNumber, onSubmitted, onRestart }: QuizSessionProps) {
  const timeLimit = timeLimitFor(questions);
  const examOnly = mode === "exam";
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [studyMode, setStudyMode] = useState(!examOnly);
  const [secondsLeft, setSecondsLeft] = useState(timeLimit);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuizSubmitResult | null>(null);
  const timesRef = useRef<Record<number, number>>({});
  const runningRef = useRef<{ id: number; at: number } | null>(null);
  const startRef = useRef(0);
  const submitRef = useRef<() => void>(() => {});

  // Per-question timing: counts while a question is on screen and not yet checked (study mode).
  useEffect(() => {
    const q = questions[index];
    if (!q || checked[q.id] || result) return;
    const started = Date.now();
    const times = timesRef.current; // same object for the whole session
    runningRef.current = { id: q.id, at: started };
    return () => {
      times[q.id] = (times[q.id] ?? 0) + (Date.now() - started);
      runningRef.current = null;
    };
  }, [index, questions, checked, result]);

  const submit = async () => {
    if (submitting || result) return;
    setSubmitting(true);
    const times = { ...timesRef.current };
    const running = runningRef.current;
    if (running) times[running.id] = (times[running.id] ?? 0) + (Date.now() - running.at);
    const spent = Math.min(36_000, Math.round((Date.now() - startRef.current) / 1000));
    const submitMode: PracticeMode = mode === "practice" ? (studyMode ? "study" : "exam") : mode;
    try {
      const data = await api<QuizSubmitResult>("/practice/submit", {
        method: "POST",
        json: {
          answers: questions.map((q) => ({ question_id: q.id, choice: answers[q.id] ?? null, time_ms: times[q.id] ? Math.min(3_600_000, Math.round(times[q.id])) : null })),
          mode: submitMode,
          part: lessonNumber ? null : part,
          lesson_number: lessonNumber,
          time_spent_seconds: spent,
        },
      });
      setResult(data);
      onSubmitted(data);
      if (data.accuracy >= 0.75) confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } });
    } catch (error) {
      toast.add({ title: "Nộp bài thất bại", description: errorMessage(error), type: "error" });
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    submitRef.current = () => void submit();
  });

  useEffect(() => {
    startRef.current = Date.now();
  }, []);

  useEffect(() => {
    if (result) return;
    const deadline = Date.now() + timeLimit * 1000;
    const timer = window.setInterval(() => {
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setSecondsLeft(left);
      if (left === 0) {
        window.clearInterval(timer);
        toast.add({ title: "Hết giờ!", description: "Bài làm được nộp tự động.", type: "warning" });
        submitRef.current();
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [timeLimit, result]);

  if (!questions.length) {
    return <div className="rounded-xl border border-slate-200 p-12 text-center text-slate-500 dark:border-slate-700">Không có câu hỏi cho bài luyện này.</div>;
  }
  if (result) return <ResultScreen result={result} questions={questions} onRestart={onRestart} />;

  const q = questions[index];
  const total = questions.length;
  const answer = answers[q.id];
  const isChecked = Boolean(checked[q.id]);
  const isCorrect = answer === q.correct_choice;
  const answeredCount = Object.keys(answers).length;
  const isLast = index === total - 1;

  const choose = (key: string) => {
    if (isChecked && studyMode) return;
    setAnswers((prev) => ({ ...prev, [q.id]: key }));
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-5 py-3 dark:border-slate-700/70 dark:bg-slate-800/80">
        <div>
          <p className="text-[11px] font-semibold text-slate-500 uppercase">{title}</p>
          <span className="text-base font-bold text-slate-900 dark:text-white">
            {q.part} • Câu {q.question_no}
          </span>
          <span className="ml-2 text-xs text-slate-500">
            ({index + 1}/{total} • đã làm {answeredCount})
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            role="timer"
            aria-label="Thời gian còn lại"
            className={cn(
              "flex items-center gap-1.5 rounded-lg border px-3 py-1 font-mono text-sm",
              secondsLeft <= 60 ? "border-red-300 text-red-600 dark:border-red-500/40 dark:text-red-400" : "border-slate-200 text-slate-700 dark:border-slate-700 dark:text-slate-300",
            )}
          >
            <Clock className="h-4 w-4" aria-hidden="true" /> {formatDuration(secondsLeft)}
          </span>
          {examOnly ? (
            <span className="rounded-lg bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 dark:bg-red-500/10 dark:text-red-300">Thi thật</span>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => setStudyMode(!studyMode)} className="cursor-pointer text-xs">
              {studyMode ? "Chế độ: Học & Giải" : "Chế độ: Thi thật"}
            </Button>
          )}
        </div>
      </div>

      <Progress value={((index + 1) / total) * 100} className="h-1.5" aria-label="Tiến độ bài làm" />

      <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700/70 dark:bg-slate-800/80">
        <div className="flex flex-wrap items-center gap-2">
          {q.difficulty && (
            <span
              className={cn(
                "inline-block rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
                q.difficulty === "easy"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
                  : q.difficulty === "hard"
                    ? "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300"
                    : "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300"
              )}
            >
              {q.difficulty === "easy" ? "Cơ bản" : q.difficulty === "hard" ? "Nâng cao" : "Tiêu chuẩn"}
            </span>
          )}
          {q.reason && (
            <span className="inline-block rounded-full border border-purple-200 bg-purple-50 px-2.5 py-0.5 text-[11px] font-semibold text-purple-700 dark:border-purple-500/30 dark:bg-purple-500/10 dark:text-purple-300">
              {q.reason}
            </span>
          )}
        </div>
        <div className="flex items-start justify-between gap-3">
          <p className="text-lg leading-relaxed font-medium text-slate-900 dark:text-slate-100">{q.sentence}</p>
          {LISTENING.has(q.part) && (
            <Button
              variant="outline"
              size="sm"
              className="shrink-0 cursor-pointer"
              onClick={() => void speak(`${q.sentence} ... ${choicesOf(q).map((c) => `${c.key}. ${c.text}`).join(" ... ")}`)}
              aria-label="Nghe câu hỏi và các lựa chọn"
            >
              <Volume2 className="h-4 w-4" /> Nghe
            </Button>
          )}
        </div>

        <div className="grid gap-3 pt-2" role="radiogroup" aria-label={`Lựa chọn cho câu ${q.question_no}`}>
          {choicesOf(q).map((choice) => {
            const selected = answer === choice.key;
            let style = "border-slate-200 bg-slate-50 text-slate-800 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200";
            if (isChecked && studyMode) {
              if (choice.key === q.correct_choice) style = "border-emerald-400 bg-emerald-50 font-semibold text-emerald-800 dark:border-emerald-500/50 dark:bg-emerald-500/15 dark:text-emerald-300";
              else if (selected) style = "border-red-400 bg-red-50 font-semibold text-red-800 dark:border-red-500/50 dark:bg-red-500/15 dark:text-red-300";
            } else if (selected) {
              style = "border-blue-500 bg-blue-50 font-semibold text-blue-800 dark:bg-blue-600/20 dark:text-blue-300";
            }
            return (
              <button
                key={choice.key}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => choose(choice.key)}
                className={cn("flex cursor-pointer items-center justify-between rounded-xl border p-4 text-left transition", style)}
              >
                <span className="flex items-center gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-xs font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">{choice.key}</span>
                  <span className="text-base">{choice.text}</span>
                </span>
                {isChecked && studyMode && choice.key === q.correct_choice && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" aria-hidden="true" />}
                {isChecked && studyMode && selected && choice.key !== q.correct_choice && <XCircle className="h-5 w-5 shrink-0 text-red-500" aria-hidden="true" />}
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 pt-4 dark:border-slate-700">
          <Button variant="ghost" disabled={index === 0} onClick={() => setIndex((i) => i - 1)} className="cursor-pointer">
            Câu trước
          </Button>
          <div className="flex items-center gap-3">
            {studyMode && !isChecked && (
              <Button disabled={!answer} onClick={() => setChecked((prev) => ({ ...prev, [q.id]: true }))} className="cursor-pointer bg-blue-600 text-white hover:bg-blue-500">
                Kiểm tra đáp án
              </Button>
            )}
            {isLast ? (
              <Button onClick={() => void submit()} disabled={submitting} className="flex cursor-pointer items-center gap-1.5 bg-emerald-600 text-white hover:bg-emerald-500">
                {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />} Nộp bài
                {answeredCount < total ? ` (${total - answeredCount} bỏ trống)` : ""}
              </Button>
            ) : (
              <Button onClick={() => setIndex((i) => i + 1)} variant="outline" className="flex cursor-pointer items-center gap-1.5">
                Câu tiếp theo <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {isChecked && studyMode && (
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-700/70 dark:bg-slate-800/80">
          <div className="flex items-center justify-between">
            <h4 className="flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white">
              <Lightbulb className="h-5 w-5 text-amber-500" aria-hidden="true" /> Phân tích 3 chiều
            </h4>
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", isCorrect ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400")}>
              {isCorrect ? "Chính xác" : "Chưa chính xác — sẽ vào Sổ lỗi khi nộp bài"}
            </span>
          </div>
          <div className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <span className="text-xs font-bold text-emerald-600 uppercase dark:text-emerald-400">Chiều 1: Căn cứ đáp án đúng ({q.correct_choice})</span>
            <p className="text-sm text-slate-700 dark:text-slate-300">{q.explanation || "Chưa có giải thích trong ngân hàng đề — hỏi AI Mentor để được phân tích."}</p>
          </div>
          {q.distractor_analysis && (
            <div className="space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
              <span className="flex items-center gap-1 text-xs font-bold text-amber-600 uppercase dark:text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> Chiều 2: Bẫy loại trừ
              </span>
              <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">{q.distractor_analysis}</p>
            </div>
          )}
          <div className="space-y-2 rounded-xl border border-purple-200 bg-purple-50/60 p-4 dark:border-purple-500/30 dark:bg-purple-950/20">
            <span className="flex items-center gap-1 text-xs font-bold text-purple-700 uppercase dark:text-purple-400">
              <Bot className="h-3.5 w-3.5" aria-hidden="true" /> Chiều 3: Paraphrase & bài học rút ra
            </span>
            <p className="text-xs text-slate-700 dark:text-slate-300">
              Mã lỗi RCA: <strong className="text-purple-700 dark:text-purple-300">[{q.error_type}]</strong>
              {q.trap_tag ? ` • ${q.trap_tag}` : ""}
            </p>
            {q.paraphrase_pair && <p className="font-mono text-xs text-slate-700 dark:text-slate-300">{q.paraphrase_pair}</p>}
            <div className="flex flex-wrap gap-3 pt-1 text-[11px] font-semibold">
              {q.lesson_number && (
                <Link href={lessonHref(q.lesson_number)} className="text-blue-600 hover:underline dark:text-blue-400">
                  Ôn Bài {String(q.lesson_number).padStart(2, "0")} →
                </Link>
              )}
              <button type="button" className="cursor-pointer text-purple-700 hover:underline dark:text-purple-400" onClick={() => askAboutQuestion(q, answer)}>
                Hỏi AI Mentor về câu này
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
