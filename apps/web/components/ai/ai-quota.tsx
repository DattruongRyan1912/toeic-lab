"use client";

import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { AIQuota } from "@/types";

/** "AI hôm nay: 3/40 lượt" for the signed-in learner (admins / unlimited accounts: no limit). */
export function AIQuotaNote({ className }: { className?: string }) {
  const { data } = useApi<AIQuota>("/ai/quota");
  if (!data || data.plan === "guest") return null;
  const low = data.remaining !== null && data.daily_quota !== null && data.remaining <= Math.max(1, Math.round(data.daily_quota * 0.1));
  return (
    <span className={cn("text-xs", low ? "font-semibold text-amber-600 dark:text-amber-400" : "text-slate-500 dark:text-slate-400", className)}>
      {data.unlimited
        ? "AI: không giới hạn lượt dùng"
        : `AI hôm nay: ${data.used_today ?? 0}/${data.daily_quota} lượt${data.remaining === 0 ? " — đã hết, làm mới lúc 0h" : ""}`}
    </span>
  );
}
