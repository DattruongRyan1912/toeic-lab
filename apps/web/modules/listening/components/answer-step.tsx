"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import { cn } from "@/lib/utils";
import type { ListeningExercise, QuizSubmitResult } from "@/types";

/**
 * Step 1 of a Part 1/2 exercise: answer from the audio (letters only, like the real test) before
 * writing the dictation. The answer goes through /practice/submit, so it counts toward listening
 * mastery, the error log and the plan like any other answered question.
 */
export function AnswerStep({ exercise }: { exercise: ListeningExercise }) {
  const keys = (["A", "B", "C", "D"] as const).filter((key) => exercise[`choice_${key.toLowerCase()}` as "choice_a"]);
  const [choice, setChoice] = useState<string | null>(null);
  const [result, setResult] = useState<QuizSubmitResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const answer = async (key: string) => {
    if (result || saving) return;
    setChoice(key);
    setSaving(true);
    setError(null);
    try {
      const graded = await api<QuizSubmitResult>("/practice/submit", {
        method: "POST",
        json: { answers: [{ question_id: exercise.id, choice: key }], mode: "practice", part: exercise.part },
      });
      setResult(graded);
      void refreshLearner();
    } catch (err) {
      setError(errorMessage(err));
      setChoice(null);
    } finally {
      setSaving(false);
    }
  };

  const outcome = result?.results[0];
  return (
    <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-900/40">
      <p className="text-xs font-semibold tracking-wider text-slate-600 uppercase dark:text-slate-300">
        Bước 1 • Nghe và chọn đáp án (chưa xem transcript)
      </p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={`Đáp án ${exercise.part} câu ${exercise.question_no}`}>
        {keys.map((key) => {
          const correct = outcome && key === outcome.correct_choice;
          const wrong = outcome && key === choice && !outcome.is_correct;
          return (
            <button
              key={key}
              type="button"
              role="radio"
              aria-checked={choice === key}
              disabled={Boolean(result) || saving}
              onClick={() => void answer(key)}
              className={cn(
                "flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg border text-sm font-bold transition disabled:cursor-default",
                correct
                  ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:border-emerald-500/50 dark:bg-emerald-500/15 dark:text-emerald-300"
                  : wrong
                    ? "border-red-400 bg-red-50 text-red-700 dark:border-red-500/50 dark:bg-red-500/15 dark:text-red-300"
                    : choice === key
                      ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-600/20 dark:text-blue-300"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
              )}
            >
              {saving && choice === key ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : key}
            </button>
          );
        })}
      </div>
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
      {outcome && (
        <p className={cn("flex items-center gap-1.5 text-xs font-semibold", outcome.is_correct ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400")}>
          {outcome.is_correct ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <XCircle className="h-4 w-4" aria-hidden="true" />}
          {outcome.is_correct ? "Chính xác!" : `Chưa đúng — đáp án (${outcome.correct_choice}).`}
          <span className="font-normal text-slate-500">
            {result?.submission_id === null ? "Đăng nhập để lưu kết quả." : outcome.is_correct ? "Đã ghi vào tiến độ Listening." : "Đã ghi vào Sổ lỗi với lịch ôn 1-3-7 ngày."}
          </span>
        </p>
      )}
      {!outcome && <p className="text-[11px] text-slate-500">Bước 2: chép chính tả cả câu hỏi và các câu trả lời để tìm chỗ nghe sót.</p>}
    </div>
  );
}
