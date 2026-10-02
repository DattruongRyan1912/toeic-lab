"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, ChevronRight, Lightbulb, Loader2, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { runTool } from "@/lib/actions";
import { askMentor } from "@/lib/mentor-store";
import { cn } from "@/lib/utils";
import type { Suggestion } from "@/types";

export function SuggestionList({
  suggestions,
  onChanged,
  compact = false,
}: {
  suggestions: Suggestion[];
  onChanged?: () => void;
  compact?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);

  if (!suggestions.length) {
    return <p className="text-xs text-slate-500 dark:text-slate-400">Không có gợi ý mới — bạn đang đi đúng kế hoạch 👍</p>;
  }

  const act = async (item: Suggestion) => {
    if (item.kind === "link" && item.href) {
      router.push(item.href);
      return;
    }
    if (item.kind === "mentor" && item.prompt) {
      askMentor(item.prompt, { pageContext: "coach" });
      return;
    }
    if (item.kind === "tool" && item.tool) {
      setBusy(item.id);
      await runTool(item.tool, item.args, { onChanged });
      setBusy(null);
    }
  };

  return (
    <ul className="space-y-2">
      {suggestions.map((item) => {
        const Icon = item.kind === "mentor" ? Bot : item.kind === "tool" ? Wand2 : Lightbulb;
        return (
          <li
            key={item.id}
            className={cn(
              "flex flex-col sm:flex-row sm:items-start gap-2.5 sm:gap-3 rounded-xl border p-3",
              item.priority >= 80
                ? "border-amber-200 bg-amber-50/60 dark:border-amber-500/30 dark:bg-amber-500/10"
                : "border-slate-200 bg-slate-50/60 dark:border-slate-700/60 dark:bg-slate-900/40",
            )}
          >
            <div className="flex items-start gap-2.5 min-w-0 flex-1">
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-purple-600 dark:text-purple-400" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 break-words">{item.title}</p>
                {!compact && <p className="mt-0.5 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400 break-words">{item.detail}</p>}
              </div>
            </div>
            <Button
              size="sm"
              variant={item.kind === "tool" ? "default" : "outline"}
              disabled={busy === item.id}
              onClick={() => void act(item)}
              className="h-7 shrink-0 cursor-pointer px-2.5 text-[11px] self-end sm:self-auto"
            >
              {busy === item.id ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : null}
              {item.cta}
              {item.kind === "link" && <ChevronRight className="h-3 w-3" aria-hidden="true" />}
            </Button>
          </li>
        );
      })}
    </ul>
  );
}
