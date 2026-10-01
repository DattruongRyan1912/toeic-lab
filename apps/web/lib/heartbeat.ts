"use client";

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

const FLUSH_EVERY_MS = 30_000;
const IDLE_AFTER_MS = 2 * 60_000; // no interaction for 2 minutes = not studying

/**
 * Tracks real study time on a page (only while the tab is visible and the learner is active)
 * and reports it to the backend in small heartbeats. `send` receives whole seconds (1-600).
 * `explicit`: a timer the learner started on purpose (e.g. listening practice in another app):
 * counts wall time without requiring page interaction or a visible tab.
 */
export function useStudyHeartbeat(active: boolean, send: (seconds: number) => Promise<unknown>, { explicit = false } = {}) {
  const sendRef = useRef(send);
  useEffect(() => {
    sendRef.current = send;
  });

  useEffect(() => {
    if (!active) return;
    let pendingMs = 0;
    let lastTick = Date.now();
    let lastInput = Date.now();

    const tick = () => {
      const now = Date.now();
      if (explicit || (document.visibilityState === "visible" && now - lastInput < IDLE_AFTER_MS)) pendingMs += now - lastTick;
      lastTick = now;
    };
    const flush = () => {
      tick();
      const seconds = Math.min(600, Math.floor(pendingMs / 1000));
      if (seconds >= 5) {
        pendingMs -= seconds * 1000;
        void sendRef.current(seconds).catch(() => undefined);
      }
    };
    const onInput = () => {
      tick();
      lastInput = Date.now();
    };
    const onVisibility = () => (document.visibilityState === "hidden" ? flush() : tick());

    const timer = window.setInterval(flush, FLUSH_EVERY_MS);
    const events = ["pointerdown", "keydown", "scroll", "wheel", "touchstart"] as const;
    events.forEach((name) => window.addEventListener(name, onInput, { passive: true }));
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(timer);
      events.forEach((name) => window.removeEventListener(name, onInput));
      document.removeEventListener("visibilitychange", onVisibility);
      flush();
    };
  }, [active, explicit]);
}

export function trackActivity(kind: "lesson" | "listening" | "reading" | "srs" | "practice" | "other", seconds: number, ref?: string) {
  return api("/learner/activity", { method: "POST", json: { kind, seconds, ref: ref ?? null } });
}
