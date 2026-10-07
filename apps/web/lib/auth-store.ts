"use client";

import { create } from "zustand";
import { api, getAuthToken, onGuestWriteBlocked, setAuthToken } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import { useMentorStore } from "@/lib/mentor-store";
import type { AuthResponse, AuthUser } from "@/types";

interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  display_name?: string;
  target_score?: number;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  isAuthModalOpen: boolean;
  authModalTab: "login" | "register";
  setAuthModalOpen: (open: boolean, tab?: "login" | "register") => void;
  openLogin: () => void;
  openRegister: () => void;
  closeAuthModal: () => void;
  initAuth: () => Promise<void>;
  login: (usernameOrEmail: string, password: string) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  loading: true,
  isAuthModalOpen: false,
  authModalTab: "login",

  setAuthModalOpen: (open, tab = "login") => set({ isAuthModalOpen: open, authModalTab: tab }),
  openLogin: () => set({ isAuthModalOpen: true, authModalTab: "login" }),
  openRegister: () => set({ isAuthModalOpen: true, authModalTab: "register" }),
  closeAuthModal: () => set({ isAuthModalOpen: false }),

  initAuth: async () => {
    const token = getAuthToken();
    if (!token) {
      set({ user: null, token: null, loading: false });
      return;
    }
    try {
      const user = await api<AuthUser>("/auth/me");
      set({ user, token, loading: false });
    } catch {
      setAuthToken(null);
      set({ user: null, token: null, loading: false });
    }
  },

  login: async (usernameOrEmail, password) => {
    const res = await api<AuthResponse>("/auth/login", {
      method: "POST",
      json: {
        username_or_email: usernameOrEmail.trim(),
        password,
      },
    });
    setAuthToken(res.access_token);
    set({ user: res.user, token: res.access_token, isAuthModalOpen: false });
    useMentorStore.setState({ messages: [], historyLoaded: false });
    void useMentorStore.getState().loadHistory();
    void refreshLearner();
    return res.user;
  },

  register: async (payload) => {
    const res = await api<AuthResponse>("/auth/register", {
      method: "POST",
      json: {
        username: payload.username.trim(),
        email: payload.email.trim(),
        password: payload.password,
        display_name: payload.display_name?.trim() || undefined,
        target_score: payload.target_score ?? 800,
      },
    });
    setAuthToken(res.access_token);
    set({ user: res.user, token: res.access_token, isAuthModalOpen: false });
    useMentorStore.setState({ messages: [], historyLoaded: false });
    void useMentorStore.getState().loadHistory();
    void refreshLearner();
    return res.user;
  },

  logout: async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // Ignore network errors on logout
    }
    setAuthToken(null);
    set({ user: null, token: null });
    useMentorStore.setState({ messages: [], historyLoaded: false });
    void refreshLearner();
  },
}));

// Guests can browse and practise, but saving progress needs an account: offer the login dialog.
onGuestWriteBlocked(() => useAuthStore.getState().openLogin());
