"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, CheckCircle2, Circle, Clock, Loader2, NotebookPen, Trash2, TrendingDown, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatDuration, percent } from "@/lib/format";
import { useStudyHeartbeat } from "@/lib/heartbeat";
import { refreshLearner } from "@/lib/learner-store";
import { cn } from "@/lib/utils";
import type { LessonDetail, LessonNote, LessonProgress } from "@/types";

type Progress = Partial<LessonProgress>;

/** Mastery strip shown under the lesson header. */
export function LessonMastery({ lesson }: { lesson: LessonDetail }) {
  const { mastery, confidence, attempts, avg_time_seconds: pace, trend } = lesson.stats;
  if (mastery == null) return null;
  const TrendIcon = trend != null && trend < 0 ? TrendingDown : TrendingUp;
  return (
    <div className="mt-3 space-y-1 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 text-slate-600 dark:text-slate-400">
        <span>
          Mức thành thạo <strong className="text-slate-900 dark:text-white">{attempts ? percent(mastery) : "chưa có dữ liệu"}</strong>
          {attempts ? ` • ${attempts} lượt • tin cậy ${Math.round((confidence ?? 0) * 100)}%` : " (đang dùng ước lượng từ điểm đầu vào)"}
        </span>
        <span className="flex items-center gap-2">
          {pace ? <span>{Math.round(pace)}s/câu</span> : null}
          {trend != null && Math.abs(trend) >= 0.05 && (
            <span className={cn("inline-flex items-center gap-0.5 font-semibold", trend < 0 ? "text-red-500" : "text-emerald-600")}>
              <TrendIcon className="h-3 w-3" aria-hidden="true" /> {trend > 0 ? "+" : ""}{Math.round(trend * 100)}%
            </span>
          )}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900" role="img" aria-label={`Mastery ${Math.round(mastery * 100)}%`}>
        <div className={cn("h-1.5 rounded-full", attempts ? (mastery >= 0.8 ? "bg-emerald-500" : mastery >= 0.6 ? "bg-amber-500" : "bg-red-500") : "bg-slate-300 dark:bg-slate-600")} style={{ width: `${Math.round(mastery * 100)}%` }} />
      </div>
    </div>
  );
}

export function LessonStudy({ lesson, onChanged }: { lesson: LessonDetail; onChanged: () => void }) {
  const number = lesson.lesson_number;
  const [progress, setProgress] = useState<Progress>(lesson.progress ?? {});
  const [notes, setNotes] = useState<LessonNote[]>(lesson.notes);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const viewed = useRef(false);

  const post = (event: "view" | "heartbeat" | "complete" | "uncomplete", seconds = 0) =>
    api<LessonProgress>(`/knowledge/lessons/${number}/progress`, { method: "POST", json: { event, seconds } });

  useEffect(() => {
    if (viewed.current) return; // StrictMode runs effects twice in dev
    viewed.current = true;
    post("view").then(setProgress, () => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useStudyHeartbeat(true, async (seconds) => setProgress(await post("heartbeat", seconds)));

  const toggleComplete = async () => {
    setBusy(true);
    try {
      setProgress(await post(progress.completed_at ? "uncomplete" : "complete"));
      if (!progress.completed_at) toast.add({ title: "Đã đánh dấu học xong", description: "Kế hoạch & lộ trình đã ghi nhận.", type: "success" });
      onChanged();
      void refreshLearner();
    } catch (error) {
      toast.add({ title: "Không cập nhật được", description: errorMessage(error), type: "error" });
    } finally {
      setBusy(false);
    }
  };

  const addNote = async (event: React.FormEvent) => {
    event.preventDefault();
    if (draft.trim().length < 2) return;
    setBusy(true);
    try {
      const note = await api<LessonNote>(`/knowledge/lessons/${number}/notes`, { method: "POST", json: { content: draft.trim() } });
      setNotes((prev) => [note, ...prev]);
      setDraft("");
    } catch (error) {
      toast.add({ title: "Không lưu được ghi chú", description: errorMessage(error), type: "error" });
    } finally {
      setBusy(false);
    }
  };

  const removeNote = async (note: LessonNote) => {
    try {
      await api(`/knowledge/lessons/${number}/notes/${note.id}`, { method: "DELETE" });
      setNotes((prev) => prev.filter((n) => n.id !== note.id));
    } catch (error) {
      toast.add({ title: "Không xoá được", description: errorMessage(error), type: "error" });
    }
  };

  const done = Boolean(progress.completed_at);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-xs dark:border-slate-700">
        <span className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
          <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" aria-hidden="true" /> Đã đọc {formatDuration(progress.time_spent_seconds ?? 0)}</span>
          <span>{progress.view_count ?? 0} lượt mở</span>
          {done && <span className="text-emerald-600 dark:text-emerald-400">Học xong {formatDate(progress.completed_at)}</span>}
        </span>
        <Button size="sm" variant={done ? "outline" : "default"} disabled={busy} onClick={() => void toggleComplete()} className="cursor-pointer">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : done ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" /> : <Circle className="h-3.5 w-3.5" aria-hidden="true" />}
          {done ? "Đã học xong (bỏ đánh dấu)" : "Đánh dấu đã học xong"}
        </Button>
      </div>

      <section className="space-y-2" aria-labelledby={`notes-${number}`}>
        <h3 id={`notes-${number}`} className="flex items-center gap-1.5 text-xs font-bold text-amber-700 uppercase dark:text-amber-400">
          <NotebookPen className="h-4 w-4" aria-hidden="true" /> Ghi chú của tôi ({notes.length})
        </h3>
        {notes.map((note) => (
          <div key={note.id} className="flex items-start justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50/50 p-2.5 text-xs dark:border-amber-500/20 dark:bg-amber-500/5">
            <span className="min-w-0 whitespace-pre-wrap text-slate-800 dark:text-slate-200">
              {note.source === "ai_mentor" && <Bot className="mr-1 inline h-3.5 w-3.5 text-purple-500" aria-label="AI ghi" />}
              {note.content}
              <span className="block text-[10px] text-slate-400">{formatDate(note.created_at, true)}</span>
            </span>
            <button type="button" onClick={() => void removeNote(note)} className="shrink-0 cursor-pointer text-red-500" aria-label="Xoá ghi chú">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        <form onSubmit={addNote} className="space-y-2">
          <label className="sr-only" htmlFor={`note-${number}`}>Ghi chú mới</label>
          <Textarea id={`note-${number}`} rows={2} maxLength={4000} value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Quy tắc tự rút ra, câu ví dụ của riêng bạn... (AI Mentor đọc được ghi chú này)" />
          <Button type="submit" size="sm" variant="outline" disabled={busy || draft.trim().length < 2} className="cursor-pointer">Lưu ghi chú</Button>
        </form>
      </section>
    </div>
  );
}
