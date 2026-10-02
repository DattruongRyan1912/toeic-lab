"use client";

import { create } from "zustand";
import { api, errorMessage } from "@/lib/api";
import type { AIStatus, DashboardStats } from "@/types";

interface LearnerState {
  stats: DashboardStats | null;
  aiStatus: AIStatus | null;
  error: string | null;
  loading: boolean;
  mobileNavOpen: boolean;
  setMobileNavOpen: (open: boolean) => void;
  refresh: () => Promise<void>;
  loadAiStatus: () => Promise<void>;
}

let inflight: Promise<void> | null = null;

/**
 * Single source of truth for learner-wide numbers (streak, due cards, open errors, current week...).
 * Any page that changes learning data calls refreshLearner() so the topbar, sidebar and dashboard stay in sync.
 */
export const useLearnerStore = create<LearnerState>((set) => ({
  stats: null,
  aiStatus: null,
  error: null,
  loading: false,
  mobileNavOpen: false,
  setMobileNavOpen: (open: boolean) => set({ mobileNavOpen: open }),
  refresh: () => {
    if (inflight) return inflight;
    set({ loading: true });
    inflight = api<DashboardStats>("/dashboard/stats")
      .then((stats) => set({ stats, error: null }))
      .catch((error: unknown) => set({ error: errorMessage(error) }))
      .finally(() => {
        inflight = null;
        set({ loading: false });
      });
    return inflight;
  },
  loadAiStatus: async () => {
    try {
      set({ aiStatus: await api<AIStatus>("/ai/status") });
    } catch {
      set({ aiStatus: null });
    }
  },
}));

export function refreshLearner(): Promise<void> {
  return useLearnerStore.getState().refresh();
}

export const PROVIDER_LABELS: Record<string, string> = {
  gemini: "Gemini",
  deepseek: "DeepSeek",
  openai: "OpenAI",
  offline: "Offline",
};
