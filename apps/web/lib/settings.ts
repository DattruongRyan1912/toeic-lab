"use client";

import { useSyncExternalStore } from "react";

export type TtsEngine = "edge" | "browser";

export interface TtsSettings {
  voice: string;
  rate: string; // "+0%", "-15%", "+15%"
  engine: TtsEngine;
}

export const DEFAULT_TTS: TtsSettings = { voice: "en-US-JennyNeural", rate: "+0%", engine: "edge" };

const STORAGE_KEY = "toeic_tts_settings";
const LEGACY_VOICE_KEY = "toeic_tts_voice";
const LEGACY_RATE_KEY = "toeic_tts_rate";
const RATE_RE = /^[+-]\d{1,2}%$/;

let cache: TtsSettings | null = null;
const listeners = new Set<() => void>();

function read(): TtsSettings {
  if (typeof window === "undefined") return DEFAULT_TTS;
  try {
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null") as Partial<TtsSettings> | null;
    const legacyVoice = window.localStorage.getItem(LEGACY_VOICE_KEY);
    const legacyRate = window.localStorage.getItem(LEGACY_RATE_KEY);
    const merged = { ...DEFAULT_TTS, ...(legacyVoice ? { voice: legacyVoice } : {}), ...(legacyRate ? { rate: legacyRate } : {}), ...stored };
    return {
      voice: typeof merged.voice === "string" && merged.voice ? merged.voice : DEFAULT_TTS.voice,
      rate: typeof merged.rate === "string" && RATE_RE.test(merged.rate) ? merged.rate : DEFAULT_TTS.rate,
      engine: merged.engine === "browser" ? "browser" : "edge",
    };
  } catch {
    return DEFAULT_TTS;
  }
}

export function getTtsSettings(): TtsSettings {
  if (cache === null) cache = read();
  return cache;
}

export function setTtsSettings(patch: Partial<TtsSettings>): void {
  cache = { ...getTtsSettings(), ...patch };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    window.localStorage.removeItem(LEGACY_VOICE_KEY);
    window.localStorage.removeItem(LEGACY_RATE_KEY);
  } catch {
    // storage may be unavailable (private mode) — keep the in-memory value
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) {
      cache = read();
      listener();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function useTtsSettings(): TtsSettings {
  return useSyncExternalStore(subscribe, getTtsSettings, () => DEFAULT_TTS);
}

/** Old settings page stored API keys in localStorage (never used, unsafe). Remove them once. */
export function purgeLegacySecrets(): void {
  try {
    window.localStorage.removeItem("toeic_deepseek_key");
    window.localStorage.removeItem("toeic_gemini_key");
  } catch {
    // ignore
  }
}
