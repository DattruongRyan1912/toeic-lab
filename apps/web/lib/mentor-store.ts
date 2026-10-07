"use client";

import { create } from "zustand";
import { api, errorMessage, getAuthToken, notifyAiQuotaUpdated } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import type { AIAction, AIActionLog, AIChatResponse, AIHistoryMessage } from "@/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions?: AIAction[];
  provider?: string;
  error?: boolean;
  hasImage?: boolean;
}

export interface SendOptions {
  questionId?: number | null;
  pageContext?: string | null;
  imageBase64?: string | null;
}

interface MentorState {
  messages: ChatMessage[];
  historyLoaded: boolean;
  sending: boolean;
  suggestions: string[];
  widgetOpen: boolean;
  widgetMinimized: boolean;
  loadHistory: () => Promise<void>;
  send: (message: string, options?: SendOptions) => Promise<void>;
  clear: () => Promise<void>;
  setWidgetOpen: (open: boolean) => void;
  setWidgetMinimized: (minimized: boolean) => void;
  markUndone: (actionId: number) => void;
}

function withUndone(actions: AIAction[] | undefined, undone: Set<number>): AIAction[] | undefined {
  return actions?.map((a) => (a.action_id && undone.has(a.action_id) ? { ...a, undone: true } : a));
}

let localId = 0;
const nextId = () => `local-${Date.now()}-${localId++}`;

export const useMentorStore = create<MentorState>((set, get) => ({
  messages: [],
  historyLoaded: false,
  sending: false,
  suggestions: [],
  widgetOpen: false,
  widgetMinimized: false,

  loadHistory: () => {
    // Concurrent callers (page mount + askMentor) await the same request.
    if (historyPromise) return historyPromise;
    if (get().historyLoaded) return Promise.resolve();
    historyPromise = loadHistoryOnce().finally(() => {
      historyPromise = null;
    });
    return historyPromise;
  },

  send: async (message, options = {}) => {
    const text = message.trim();
    if (!text || get().sending) return;
    if (!getAuthToken()) {
      set((state) => ({
        messages: [
          ...state.messages,
          {
            id: nextId(),
            role: "assistant",
            content: "🔒 **Yêu cầu đăng nhập**: Vui lòng đăng nhập tài khoản để trò chuyện và nhận phân tích cá nhân hóa từ AI Mentor.",
            error: true,
          },
        ],
      }));
      return;
    }
    set((state) => ({
      sending: true,
      suggestions: [],
      messages: [...state.messages, { id: nextId(), role: "user", content: text, hasImage: Boolean(options.imageBase64) }],
    }));
    try {
      const data = await api<AIChatResponse>("/ai/chat", {
        method: "POST",
        json: {
          message: text,
          question_id: options.questionId ?? null,
          page_context: options.pageContext ?? null,
          image_base64: options.imageBase64 ?? null,
        },
      });
      set((state) => ({
        messages: [
          ...state.messages,
          { id: nextId(), role: "assistant", content: data.reply, actions: data.actions_taken, provider: data.provider },
        ],
        suggestions: data.suggested_questions,
      }));
      if (data.actions_taken.some((action) => action.status === "success" && action.writes !== false)) void refreshLearner();
      notifyAiQuotaUpdated();
    } catch (error) {
      set((state) => ({
        messages: [
          ...state.messages,
          { id: nextId(), role: "assistant", content: `⚠️ ${errorMessage(error)}`, error: true },
        ],
      }));
    } finally {
      set({ sending: false });
    }
  },

  clear: async () => {
    set({ messages: [], suggestions: [] });
    try {
      await api("/ai/history", { method: "DELETE" });
    } catch {
      // history stays on the server; the local thread is still cleared
    }
  },

  setWidgetOpen: (open) => set({ widgetOpen: open, widgetMinimized: false }),
  setWidgetMinimized: (minimized) => set({ widgetMinimized: minimized }),
  markUndone: (actionId) =>
    set((state) => ({ messages: state.messages.map((m) => ({ ...m, actions: withUndone(m.actions, new Set([actionId])) })) })),
}));

let historyPromise: Promise<void> | null = null;

async function loadHistoryOnce(): Promise<void> {
  const { getState: get, setState: set } = useMentorStore;
  if (get().historyLoaded) return;
  if (!getAuthToken()) {
    set({ historyLoaded: false, messages: [] });
    return;
  }
  set({ historyLoaded: true });
  try {
    const [history, log] = await Promise.all([
      api<AIHistoryMessage[]>("/ai/history?limit=60"),
      api<AIActionLog[]>("/ai/actions?limit=200").catch(() => [] as AIActionLog[]),
    ]);
    const undone = new Set(log.filter((a) => a.status === "undone").map((a) => a.id));
    if (get().messages.length === 0) {
      set({
        messages: history.map((m) => ({ id: `db-${m.id}`, role: m.role, content: m.content, actions: withUndone(m.actions, undone) })),
      });
    }
  } catch {
    set({ historyLoaded: false });
  }
}

/** Open the floating mentor and ask a question with optional grounding (question pointer / page). */
export function askMentor(prompt: string, options: SendOptions = {}): void {
  const token = getAuthToken();
  if (!token) {
    import("@/lib/auth-store").then(({ useAuthStore }) => {
      useAuthStore.getState().openLogin();
    });
    return;
  }
  const store = useMentorStore.getState();
  store.setWidgetOpen(true);
  void store.loadHistory().then(() => useMentorStore.getState().send(prompt, options));
}

export const WELCOME_MESSAGE =
  "Xin chào! Tôi là **TOEIC AI Mentor** — tôi đọc được tiến độ học, Sổ lỗi và ngân hàng đề của bạn. " +
  "Hãy hỏi về một câu Part 5, một từ vựng, hoặc nhờ tôi *lưu câu sai / thêm thẻ từ / đặt lịch nhắc*.";
