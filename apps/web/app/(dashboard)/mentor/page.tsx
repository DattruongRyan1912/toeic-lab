"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Bot, History, Lightbulb, Lock, LogIn, MessageSquare, Mic, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ActionLog } from "@/components/ai/action-log";
import { SuggestionList } from "@/components/coach/suggestion-list";
import { ChatComposer, ChatThread, SuggestionChips } from "@/components/mentor/chat";
import { LoadingState } from "@/components/states";
import { VoiceStudio } from "@/modules/mentor/components/voice-studio";
import { useAuthStore } from "@/lib/auth-store";
import { PROVIDER_LABELS, useLearnerStore } from "@/lib/learner-store";
import { useMentorStore } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { Suggestion } from "@/types";

const QUICK_PROMPTS = [
  "Hôm nay tôi nên học gì?",
  "Phân tích lỗ hổng lớn nhất của tôi",
  "Tạo 5 câu luyện cho chuyên đề yếu nhất của tôi",
  "Lập lại kế hoạch tuần cho tôi",
];

/** Sends `?prompt=` once (links from the plan / coach), then drops it from the URL. */
function PromptFromUrl({ isAuth }: { isAuth: boolean }) {
  const params = useSearchParams();
  const router = useRouter();
  const sent = useRef<string | null>(null);
  const prompt = params.get("prompt");

  useEffect(() => {
    if (!isAuth || !prompt || sent.current === prompt) return;
    sent.current = prompt;
    const { loadHistory } = useMentorStore.getState();
    void loadHistory().then(() => useMentorStore.getState().send(prompt, { pageContext: "/mentor" }));
    router.replace("/mentor", { scroll: false });
  }, [isAuth, prompt, router]);
  return null;
}

function AuthLockCard({
  title = "Đăng nhập để sử dụng AI Mentor Copilot",
  description = "Huấn luyện viên cá nhân AI Mentor cần liên kết với tài khoản học viên để nắm bắt trình độ hiện tại, cá nhân hóa lộ trình, theo dõi câu sai và ghi nhớ tiến độ của bạn.",
  openLogin,
  openRegister,
}: {
  title?: string;
  description?: string;
  openLogin: () => void;
  openRegister: () => void;
}) {
  return (
    <div className="flex h-full min-h-[360px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white/70 p-6 text-center backdrop-blur-xs sm:p-10 dark:border-slate-700/80 dark:bg-slate-800/40">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/25">
        <Lock className="h-8 w-8" />
      </div>
      <span className="mb-2 inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
        🔒 Yêu cầu đăng nhập tài khoản
      </span>
      <h3 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">
        {title}
      </h3>
      <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
        {description}
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button onClick={openLogin} className="cursor-pointer bg-blue-600 px-5 text-xs font-semibold text-white shadow-xs hover:bg-blue-500">
          <LogIn className="mr-1.5 h-4 w-4" /> Đăng nhập ngay
        </Button>
        <Button variant="outline" onClick={openRegister} className="cursor-pointer text-xs font-medium">
          Tạo tài khoản mới
        </Button>
      </div>
      <div className="mt-8 grid max-w-lg grid-cols-1 gap-3 text-left sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3.5 text-xs dark:border-slate-800 dark:bg-slate-900/40">
          <span className="font-semibold text-slate-800 dark:text-slate-200">🎯 Cá nhân hoá chuyên sâu</span>
          <p className="mt-1 text-slate-500 dark:text-slate-400">AI giải đáp theo đúng mục tiêu điểm (600, 750, 850+) và chuyên đề bạn đang yếu.</p>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3.5 text-xs dark:border-slate-800 dark:bg-slate-900/40">
          <span className="font-semibold text-slate-800 dark:text-slate-200">📚 Tự động lưu Sổ lỗi & SRS</span>
          <p className="mt-1 text-slate-500 dark:text-slate-400">Tự động phân tích bẫy đề thi và lưu câu làm sai vào Sổ tay ôn tập 1→3→7 ngày.</p>
        </div>
      </div>
    </div>
  );
}

function Aside({ refreshKey, isAuth }: { refreshKey: number; isAuth: boolean }) {
  const suggestions = useApi<Suggestion[]>(isAuth ? `/learner/suggestions?v=${refreshKey}` : null);
  const openLogin = useAuthStore((state) => state.openLogin);

  return (
    <aside className="hidden min-h-0 flex-col gap-4 overflow-y-auto lg:flex">
      <Card className="space-y-3 border-slate-200 bg-white p-4 dark:border-slate-700/70 dark:bg-slate-800/80">
        <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <Lightbulb className="h-4 w-4 text-amber-500" aria-hidden="true" /> Gợi ý từ dữ liệu của bạn
        </h2>
        {!isAuth ? (
          <div className="py-4 text-center text-xs text-slate-500 space-y-2">
            <p>Đăng nhập để AI phân tích và đưa ra gợi ý học tập sát thực tế.</p>
            <Button size="sm" variant="outline" onClick={openLogin} className="cursor-pointer text-xs">
              Đăng nhập
            </Button>
          </div>
        ) : suggestions.data ? (
          <SuggestionList suggestions={suggestions.data.slice(0, 4)} onChanged={suggestions.reload} compact />
        ) : (
          <LoadingState label="Đang phân tích..." />
        )}
      </Card>
      <Card className="space-y-3 border-slate-200 bg-white p-4 dark:border-slate-700/70 dark:bg-slate-800/80">
        <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <History className="h-4 w-4 text-purple-500" aria-hidden="true" /> AI đã thay đổi gì
        </h2>
        {!isAuth ? (
          <p className="py-4 text-center text-xs text-slate-500">
            Đăng nhập để xem nhật ký thao tác tự động của AI.
          </p>
        ) : (
          <ActionLog limit={12} refreshKey={refreshKey} />
        )}
      </Card>
    </aside>
  );
}

function MentorContent() {
  const params = useSearchParams();
  const tabParam = params.get("tab");
  const [viewMode, setViewMode] = useState<"chat" | "voice">(tabParam === "voice" ? "voice" : "chat");

  const { messages, sending, suggestions, loadHistory, send, clear } = useMentorStore();
  const aiStatus = useLearnerStore((state) => state.aiStatus);
  const user = useAuthStore((state) => state.user);
  const authLoading = useAuthStore((state) => state.loading);
  const openLogin = useAuthStore((state) => state.openLogin);
  const openRegister = useAuthStore((state) => state.openRegister);

  const isAuth = Boolean(user);
  const writes = messages.reduce((sum, m) => sum + (m.actions?.filter((a) => a.writes !== false).length ?? 0), 0);

  useEffect(() => {
    if (isAuth) {
      void loadHistory();
    }
  }, [isAuth, loadHistory]);

  const ask = (text: string, options?: { imageBase64?: string | null }) => {
    if (!isAuth) {
      openLogin();
      return;
    }
    void send(text, { pageContext: "/mentor", imageBase64: options?.imageBase64 ?? null });
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-6xl flex-col space-y-4">
      <Suspense fallback={null}>
        <PromptFromUrl isAuth={isAuth} />
      </Suspense>

      {/* Header bar with Mode Switcher */}
      <div className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            <Bot className="h-6 w-6 text-blue-500" aria-hidden="true" /> AI Mentor Copilot
            {aiStatus && (
              <span className="rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-xs font-normal text-purple-700 dark:border-purple-500/20 dark:bg-purple-500/10 dark:text-purple-400">
                {PROVIDER_LABELS[aiStatus.provider] ?? aiStatus.provider}
                {aiStatus.model ? ` · ${aiStatus.model}` : ""}
              </span>
            )}
            {!authLoading && !isAuth && (
              <span className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
                Chưa đăng nhập
              </span>
            )}
          </h1>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Huấn luyện viên cá nhân: Hỏi đáp ngữ pháp, tra cứu phân tích câu sai hoặc đàm thoại giọng nói 1-1 trực tiếp.
          </p>
        </div>

        {/* View Mode Toggle & Clear Button */}
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-xl border border-slate-200 bg-slate-100 p-1 dark:border-slate-800 dark:bg-slate-900">
            <button
              type="button"
              onClick={() => setViewMode("chat")}
              className={cn(
                "cursor-pointer flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-semibold transition",
                viewMode === "chat"
                  ? "bg-white text-slate-900 shadow-xs dark:bg-slate-800 dark:text-white"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200",
              )}
            >
              <MessageSquare className="h-3.5 w-3.5" /> Chat Copilot
            </button>
            <button
              type="button"
              onClick={() => setViewMode("voice")}
              className={cn(
                "cursor-pointer flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-semibold transition",
                viewMode === "voice"
                  ? "bg-blue-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200",
              )}
            >
              <Mic className="h-3.5 w-3.5" /> Luyện Nói 1-1 (Voice Studio)
            </button>
          </div>

          {viewMode === "chat" && isAuth && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => void clear()}
              disabled={!messages.length || sending}
              className="shrink-0 cursor-pointer text-xs"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" aria-hidden="true" /> Xóa chat
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === "voice" ? (
        <div className="flex-1 min-h-0">
          {!authLoading && !isAuth ? (
            <AuthLockCard
              title="Đăng nhập để luyện nói trong Voice Studio"
              description="Tính năng luyện nói 1-1 và chấm điểm phát âm theo thời gian thực yêu cầu đăng nhập tài khoản để lưu lại lịch sử hội thoại và đánh giá tiến độ."
              openLogin={openLogin}
              openRegister={openRegister}
            />
          ) : (
            <VoiceStudio />
          )}
        </div>
      ) : (
        <div className="grid flex-1 min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="flex min-h-0 flex-col space-y-4">
            {aiStatus?.offline && (
              <p className="shrink-0 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
                ⚙️ Chưa cấu hình API key — Mentor chạy <strong>chế độ offline</strong>: trả lời từ dữ liệu học của bạn và hiểu các lệnh như “Kế hoạch hôm nay”, “Điểm yếu”, “Lập lại kế hoạch”, “Ghi nhớ: …”.
                Thêm <code>GEMINI_API_KEY</code> hoặc <code>DEEPSEEK_API_KEY</code> vào <code>.env</code> để bật AI. <Link href="/settings" className="font-semibold underline">Xem cài đặt</Link>
              </p>
            )}

            <Card className="flex min-h-0 flex-1 flex-col overflow-hidden border-slate-200 bg-white p-0 dark:border-slate-700/70 dark:bg-slate-800/80">
              <div className="flex-1 overflow-y-auto p-5">
                {!authLoading && !isAuth ? (
                  <AuthLockCard
                    title="Đăng nhập để trò chuyện cùng AI Mentor"
                    description="Huấn luyện viên cá nhân cần liên kết với tài khoản học viên để nắm bắt trình độ hiện tại, theo dõi lỗ hổng Part 1–7, ghi nhớ lỗi sai và điều chỉnh lộ trình học riêng cho bạn."
                    openLogin={openLogin}
                    openRegister={openRegister}
                  />
                ) : (
                  <ChatThread messages={messages} sending={sending} />
                )}
              </div>
              <div className="shrink-0 border-t border-slate-100 bg-slate-50 p-3 dark:border-slate-700/60 dark:bg-slate-900/40">
                <SuggestionChips
                  items={suggestions.length ? suggestions : QUICK_PROMPTS}
                  disabled={sending || !isAuth}
                  onPick={(value) => (isAuth ? ask(value) : openLogin())}
                />
              </div>
              <div className="shrink-0 border-t border-slate-200 p-4 dark:border-slate-700">
                <ChatComposer
                  onSend={ask}
                  sending={sending}
                  disabled={!isAuth}
                  onClick={!isAuth ? openLogin : undefined}
                  allowImage={Boolean(aiStatus?.vision) && isAuth}
                  placeholder={
                    isAuth
                      ? "Hỏi về ngữ pháp, từ vựng, hoặc dán câu hỏi Part 5... (Enter để gửi, Shift+Enter xuống dòng)"
                      : "🔒 Vui lòng đăng nhập để gửi câu hỏi cho AI Mentor..."
                  }
                />
              </div>
            </Card>
          </div>
          <Aside refreshKey={writes} isAuth={isAuth} />
        </div>
      )}
    </div>
  );
}

export default function MentorPage() {
  return (
    <Suspense fallback={<LoadingState label="Đang tải AI Mentor Copilot..." />}>
      <MentorContent />
    </Suspense>
  );
}
