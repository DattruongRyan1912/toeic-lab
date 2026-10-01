"use client";

import { useState } from "react";
import { History, Loader2, Undo2 } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/states";
import { TOOL_LABELS, undoAction } from "@/lib/actions";
import { formatDate } from "@/lib/format";
import { useMentorStore } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { AIActionLog } from "@/types";

const SOURCES: Record<string, string> = { ai_mentor: "AI Mentor", coach: "Gợi ý 1 chạm", user: "Bạn" };

/** Audit trail of data changes made through agent tools. `refreshKey` refetches when it changes. */
export function ActionLog({ limit = 20, refreshKey = 0 }: { limit?: number; refreshKey?: number }) {
  const log = useApi<AIActionLog[]>(`/ai/actions?limit=${limit}&v=${refreshKey}`);
  const markUndone = useMentorStore((state) => state.markUndone);
  const [busy, setBusy] = useState<number | null>(null);

  if (log.error) return <ErrorState message={log.error} onRetry={log.reload} />;
  if (!log.data) return <LoadingState label="Đang tải nhật ký..." />;
  if (!log.data.length) {
    return <p className="text-xs text-slate-500 dark:text-slate-400">Chưa có thay đổi nào do AI thực hiện. Mọi thay đổi sau này sẽ hiện ở đây và hoàn tác được.</p>;
  }

  const undo = async (item: AIActionLog) => {
    setBusy(item.id);
    if (await undoAction(item.id)) {
      markUndone(item.id);
      log.mutate((prev) => prev?.map((a) => (a.id === item.id ? { ...a, status: "undone" } : a)));
    }
    setBusy(null);
  };

  return (
    <ul className="space-y-1.5" aria-label="Nhật ký thao tác AI">
      {log.data.map((item) => {
        const undone = item.status === "undone";
        return (
          <li key={item.id} className="flex items-start gap-2 rounded-lg border border-slate-200 p-2 text-[11px] dark:border-slate-700">
            <History className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", undone ? "text-slate-400" : "text-purple-500")} aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className={cn("font-semibold text-slate-800 dark:text-slate-200", undone && "line-through opacity-60")}>
                {TOOL_LABELS[item.tool] ?? item.tool}
              </p>
              {item.summary && <p className={cn("text-slate-600 dark:text-slate-400", undone && "opacity-60")}>{item.summary}</p>}
              <p className="text-[10px] text-slate-400">
                {SOURCES[item.source ?? ""] ?? item.source} • {formatDate(item.created_at, true)}
                {undone && item.undone_at ? ` • đã hoàn tác ${formatDate(item.undone_at, true)}` : ""}
              </p>
            </div>
            {undone ? (
              <span className="shrink-0 text-[10px] font-semibold text-slate-400">Đã hoàn tác</span>
            ) : item.undoable ? (
              <button
                type="button"
                disabled={busy === item.id}
                onClick={() => void undo(item)}
                className="inline-flex shrink-0 cursor-pointer items-center gap-1 font-semibold text-slate-600 hover:underline disabled:opacity-50 dark:text-slate-300"
                aria-label={`Hoàn tác: ${item.summary ?? item.tool}`}
              >
                {busy === item.id ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : <Undo2 className="h-3 w-3" aria-hidden="true" />} Hoàn tác
              </button>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
