"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Bot, Maximize2, Minus, RotateCcw, X } from "lucide-react";
import { ChatComposer, ChatThread, SuggestionChips } from "@/components/mentor/chat";
import { PROVIDER_LABELS, useLearnerStore } from "@/lib/learner-store";
import { useMentorStore } from "@/lib/mentor-store";
import { cn } from "@/lib/utils";

function pagePrompts(pathname: string): string[] {
  if (pathname.startsWith("/mock-tests")) return ["Mẹo làm Part 5 dưới 15 giây/câu", "Tại sao chọn trạng từ thay vì tính từ?", "Phân bổ 75 phút Reading thế nào?"];
  if (pathname.startsWith("/vocab")) return ["Cho 3 collocation ăn điểm với 'comply'", "Phân biệt postpone / delay / cancel", "Lưu từ 'reimburse' vào Sổ tay"];
  if (pathname.startsWith("/lessons")) return ["Tóm tắt quy tắc bài tôi yếu nhất", "Cho 3 câu luyện vị trí trạng từ", "Bẫy đuôi -ly là tính từ gồm những từ nào?"];
  if (pathname.startsWith("/error-log")) return ["Phân tích lỗ hổng lớn nhất của tôi", "Kế hoạch 7 ngày khắc phục lỗi GRAMMAR", "Quy tắc vàng tránh bẫy [TRAP]"];
  if (pathname.startsWith("/roadmaps")) return ["Tuần này tôi nên tập trung gì?", "Tôi đang chậm tiến độ, điều chỉnh sao?", "Đặt lịch nhắc tôi học lúc 21:00"];
  return ["Hôm nay tôi nên học gì?", "Phân tích lỗ hổng lớn nhất của tôi", "Chiến thuật đạt 800+ cho backend dev"];
}

export function AiCopilotWidget() {
  const pathname = usePathname();
  const { messages, sending, suggestions, widgetOpen, widgetMinimized, loadHistory, send, clear, setWidgetOpen, setWidgetMinimized } =
    useMentorStore();
  const aiStatus = useLearnerStore((state) => state.aiStatus);

  useEffect(() => {
    if (widgetOpen) void loadHistory();
  }, [widgetOpen, loadHistory]);

  if (pathname.startsWith("/mentor")) return null; // the full page already shows the same conversation

  const providerLabel = aiStatus ? `${PROVIDER_LABELS[aiStatus.provider] ?? aiStatus.provider}${aiStatus.model ? ` · ${aiStatus.model}` : ""}` : "Đang kết nối...";
  const chips = suggestions.length ? suggestions : pagePrompts(pathname);
  const ask = (text: string, options?: { imageBase64?: string | null }) =>
    void send(text, { pageContext: pathname, imageBase64: options?.imageBase64 ?? null });

  if (!widgetOpen) {
    return (
      <button
        type="button"
        onClick={() => setWidgetOpen(true)}
        className="group fixed right-4 bottom-20 md:right-6 md:bottom-6 z-40 flex cursor-pointer items-center gap-3 rounded-full border border-white/20 bg-gradient-to-r from-blue-600 to-indigo-600 p-3 text-white shadow-xl shadow-blue-500/25 transition-all hover:scale-105 hover:shadow-blue-500/40 active:scale-95 sm:px-4 sm:py-3"
        aria-label="Mở trợ lý AI Mentor"
      >
        <span className="relative">
          <Bot className="h-5 w-5" aria-hidden="true" />
          <span className={cn("absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full border-2 border-slate-900", aiStatus?.offline ? "bg-amber-400" : "bg-emerald-400")} />
        </span>
        <span className="hidden text-xs font-bold tracking-wide sm:inline">AI Mentor Copilot</span>
      </button>
    );
  }

  return (
    <section
      aria-label="AI Mentor Copilot"
      className={cn(
        "fixed right-3 bottom-20 md:right-6 md:bottom-6 z-50 flex w-[calc(100vw-1.5rem)] max-w-[420px] flex-col overflow-hidden rounded-2xl border border-slate-300 bg-white/95 shadow-2xl backdrop-blur-2xl transition-all duration-300 dark:border-slate-700/80 dark:bg-[#11192e]/95",
        widgetMinimized ? "h-14" : "h-[540px] max-h-[75vh] md:h-[600px] md:max-h-[85vh]",
      )}
    >
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-slate-100/90 px-4 dark:border-slate-800/80 dark:bg-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-blue-200 bg-blue-50 text-blue-600 dark:border-blue-500/40 dark:bg-blue-600/30 dark:text-blue-400">
            <Bot className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <Link href="/mentor" className="block text-xs leading-tight font-bold text-slate-900 hover:underline dark:text-slate-100">
              AI Mentor Copilot
            </Link>
            <span className="font-mono text-[10px] text-slate-500 dark:text-slate-400">{providerLabel}</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {!widgetMinimized && (
            <button type="button" onClick={() => void clear()} className="cursor-pointer rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-200/60 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-700/50 dark:hover:text-slate-200" aria-label="Xóa lịch sử trò chuyện">
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          )}
          <button type="button" onClick={() => setWidgetMinimized(!widgetMinimized)} className="cursor-pointer rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-200/60 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-700/50 dark:hover:text-slate-200" aria-label={widgetMinimized ? "Mở rộng" : "Thu nhỏ"}>
            {widgetMinimized ? <Maximize2 className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
          </button>
          <button type="button" onClick={() => setWidgetOpen(false)} className="cursor-pointer rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-200/60 hover:text-red-500 dark:text-slate-400 dark:hover:bg-slate-700/50" aria-label="Đóng">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {!widgetMinimized && (
        <>
          <div className="flex-1 overflow-y-auto p-4">
            <ChatThread messages={messages} sending={sending} compact />
          </div>
          <div className="shrink-0 border-t border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800/80 dark:bg-slate-900/60">
            <SuggestionChips items={chips} disabled={sending} onPick={(value) => ask(value)} />
          </div>
          <div className="shrink-0 border-t border-slate-200 bg-white p-3 dark:border-slate-800/80 dark:bg-slate-900/90">
            <ChatComposer onSend={ask} sending={sending} allowImage={Boolean(aiStatus?.vision)} compact />
          </div>
        </>
      )}
    </section>
  );
}
