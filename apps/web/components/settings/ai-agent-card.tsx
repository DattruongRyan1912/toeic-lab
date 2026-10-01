"use client";

import { Eye, PencilLine, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActionLog } from "@/components/ai/action-log";
import { LoadingState } from "@/components/states";
import { TOOL_LABELS } from "@/lib/actions";
import { useApi } from "@/lib/use-api";
import type { AIToolInfo } from "@/types";

export function AiAgentCard() {
  const tools = useApi<AIToolInfo[]>("/ai/tools");
  const reads = tools.data?.filter((t) => !t.writes) ?? [];
  const writes = tools.data?.filter((t) => t.writes) ?? [];

  return (
    <Card id="ai-actions" className="scroll-mt-20 border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
        <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
          <ShieldCheck className="h-5 w-5 text-emerald-500" aria-hidden="true" /> AI Mentor được làm gì
        </CardTitle>
        <p className="text-[11px] text-slate-500">AI chỉ thay đổi dữ liệu khi bạn yêu cầu. Mọi thay đổi được ghi lại kèm dữ liệu cũ và hoàn tác được.</p>
      </CardHeader>
      <CardContent className="grid gap-5 pt-4 md:grid-cols-2">
        <div className="space-y-3 text-xs">
          {!tools.data ? (
            <LoadingState />
          ) : (
            <>
              <div>
                <p className="mb-1.5 flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                  <Eye className="h-3.5 w-3.5 text-blue-500" aria-hidden="true" /> Đọc ({reads.length})
                </p>
                <ul className="flex flex-wrap gap-1.5">
                  {reads.map((t) => (
                    <li key={t.name} title={t.description} className="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600 dark:border-slate-700 dark:text-slate-300">
                      {TOOL_LABELS[t.name] ?? t.name}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-1.5 flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                  <PencilLine className="h-3.5 w-3.5 text-purple-500" aria-hidden="true" /> Thay đổi ({writes.length})
                </p>
                <ul className="flex flex-wrap gap-1.5">
                  {writes.map((t) => (
                    <li key={t.name} title={t.description} className="rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-[11px] text-purple-700 dark:border-purple-500/30 dark:bg-purple-500/10 dark:text-purple-300">
                      {TOOL_LABELS[t.name] ?? t.name}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">Nhật ký thay đổi gần đây</p>
          <div className="max-h-80 overflow-y-auto pr-1">
            <ActionLog limit={30} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
