"use client";

import { getTtsSettings, type TtsSettings } from "@/lib/settings";

let currentAudio: HTMLAudioElement | null = null;

export function stopSpeaking(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
}

function playEdge(text: string, settings: TtsSettings): Promise<void> {
  const params = new URLSearchParams({ text, voice: settings.voice, rate: settings.rate });
  const audio = new Audio(`/api/tts?${params.toString()}`);
  currentAudio = audio;
  return new Promise((resolve, reject) => {
    audio.onended = () => resolve();
    audio.onerror = () => reject(new Error("Edge TTS unavailable"));
    audio.play().catch(reject);
  });
}

function speakBrowser(text: string, settings: TtsSettings): Promise<void> {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return Promise.resolve();
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = settings.voice.slice(0, 5) || "en-US"; // "en-GB-SoniaNeural" -> "en-GB"
    const percent = Number.parseInt(settings.rate, 10);
    utterance.rate = Number.isFinite(percent) ? Math.min(2, Math.max(0.5, 1 + percent / 100)) : 1;
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    window.speechSynthesis.speak(utterance);
  });
}

/**
 * Speak English text with the learner's chosen ETS voice (Settings page).
 * Edge TTS goes through the backend (disk-cached MP3); the browser voice is the offline fallback.
 */
export async function speak(text: string, overrides: Partial<TtsSettings> = {}): Promise<void> {
  const clean = text.trim();
  if (!clean) return;
  const settings = { ...getTtsSettings(), ...overrides };
  stopSpeaking();
  if (settings.engine === "edge") {
    try {
      await playEdge(clean.slice(0, 1000), settings);
      return;
    } catch {
      // backend or network unavailable -> browser voice
    }
  }
  await speakBrowser(clean, settings);
}
