"use client";

import { useState } from "react";
import { Brain, Loader2, Pin, PinOff, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { LearnerMemory } from "@/types";

const CATEGORIES: Record<LearnerMemory["category"], string> = {
  goal: "Mục tiêu",
  preference: "Sở thích học",
  struggle: "Điểm yếu",
  strength: "Điểm mạnh",
  context: "Bối cảnh",
  other: "Khác",
};
const SOURCES: Record<string, string> = { ai_mentor: "AI ghi", user: "Bạn ghi", onboarding: "Onboarding", coach: "Gợi ý" };

export function MemoriesCard() {
  const memories = useApi<LearnerMemory[]>("/learner/memories");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<LearnerMemory["category"]>("preference");
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<void>, failTitle: string) => {
    setBusy(true);
    try {
      await action();
    } catch (err) {
      toast.add({ title: failTitle, description: errorMessage(err), type: "error" });
    } finally {
      setBusy(false);
    }
  };

  const add = (event: React.FormEvent) => {
    event.preventDefault();
    if (content.trim().length < 3) return;
    void run(async () => {
      const created = await api<LearnerMemory>("/learner/memories", { method: "POST", json: { content: content.trim(), category, pinned: false } });
      memories.mutate((prev) => [created, ...(prev ?? [])]);
      setContent("");
    }, "Không lưu được");
  };

  const togglePin = (memory: LearnerMemory) =>
    void run(async () => {
      const updated = await api<LearnerMemory>(`/learner/memories/${memory.id}`, { method: "PATCH", json: { pinned: !memory.pinned } });
      memories.mutate((prev) => prev?.map((m) => (m.id === updated.id ? updated : m)));
    }, "Không cập nhật được");

  const remove = (memory: LearnerMemory) =>
    void run(async () => {
      await api(`/learner/memories/${memory.id}`, { method: "DELETE" });
      memories.mutate((prev) => prev?.filter((m) => m.id !== memory.id));
    }, "Không xoá được");

  return (
    <Card id="memories" className="scroll-mt-20 border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
        <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
          <Brain className="h-5 w-5 text-purple-500" aria-hidden="true" /> AI Mentor nhớ gì về bạn
        </CardTitle>
        <p className="text-[11px] text-slate-500">Được đưa vào mọi cuộc trò chuyện. Mục ghim luôn được ưu tiên. Nói với Mentor “Ghi nhớ: …” để thêm nhanh.</p>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        {memories.error ? (
          <ErrorState message={memories.error} onRetry={memories.reload} />
        ) : !memories.data ? (
          <LoadingState />
        ) : memories.data.length === 0 ? (
          <p className="text-xs text-slate-500">Chưa có ghi nhớ nào.</p>
        ) : (
          <ul className="space-y-2">
            {memories.data.map((m) => (
              <li key={m.id} className={cn("flex items-start justify-between gap-3 rounded-lg border p-2.5 text-xs", m.pinned ? "border-purple-200 bg-purple-50/50 dark:border-purple-500/30 dark:bg-purple-500/10" : "border-slate-200 dark:border-slate-700")}>
                <span className="min-w-0">
                  <span className="mr-1.5 rounded bg-slate-100 px-1.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{CATEGORIES[m.category] ?? m.category}</span>
                  <span className="text-slate-800 dark:text-slate-200">{m.content}</span>
                  <span className="block text-[10px] text-slate-400">{SOURCES[m.source] ?? m.source} • {formatDate(m.updated_at ?? m.created_at, true)}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <button type="button" disabled={busy} onClick={() => togglePin(m)} className="cursor-pointer text-slate-500 hover:text-purple-600" aria-label={m.pinned ? "Bỏ ghim" : "Ghim"}>
                    {m.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
                  </button>
                  <button type="button" disabled={busy} onClick={() => remove(m)} className="cursor-pointer text-red-500" aria-label={`Xoá ghi nhớ: ${m.content}`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={add} className="grid gap-2 border-t border-slate-100 pt-3 sm:grid-cols-[130px_1fr_auto] dark:border-slate-700/60">
          <label className="sr-only" htmlFor="mem-cat">Loại</label>
          <select id="mem-cat" value={category} onChange={(e) => setCategory(e.target.value as LearnerMemory["category"])} className="rounded-lg border border-slate-200 bg-transparent p-2 text-xs dark:border-slate-700">
            {Object.entries(CATEGORIES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <label className="sr-only" htmlFor="mem-content">Nội dung</label>
          <Input id="mem-content" value={content} onChange={(e) => setContent(e.target.value)} maxLength={500} placeholder="VD: Thích ví dụ về code review, deploy, sprint planning" />
          <Button type="submit" disabled={busy || content.trim().length < 3} className="cursor-pointer">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null} Thêm
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
