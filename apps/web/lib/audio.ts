"use client";

import { getTtsSettings, type TtsSettings } from "@/lib/settings";

let currentAudio: HTMLAudioElement | null = null;

// --- Prefetch: the first Edge TTS request for a sentence is synthesised on the server (~3-4 s); fetching the
// next cards' audio ahead of time makes the "listen" button play instantly. Keyed by the exact TTS URL, so a
// voice/rate change simply misses and re-fetches.
const MAX_PREFETCHED = 40;
const MAX_PARALLEL = 2;
const prefetched = new Map<string, Promise<string | null>>(); // TTS URL -> blob URL (null if it failed)
const waiting: (() => void)[] = [];
let running = 0;

function ttsUrl(text: string, settings: TtsSettings): string {
  const params = new URLSearchParams({ text: text.slice(0, 1000), voice: settings.voice, rate: settings.rate });
  return `/api/tts?${params.toString()}`;
}

function limited<T>(task: () => Promise<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const start = () => {
      running += 1;
      task()
        .then(resolve, reject)
        .finally(() => {
          running -= 1;
          waiting.shift()?.();
        });
    };
    if (running < MAX_PARALLEL) start();
    else waiting.push(start);
  });
}

function evictOldest(): void {
  while (prefetched.size > MAX_PREFETCHED) {
    const [url, blobUrl] = prefetched.entries().next().value as [string, Promise<string | null>];
    prefetched.delete(url);
    void blobUrl.then((value) => value && URL.revokeObjectURL(value));
  }
}

/** Warm the audio of texts the learner is about to hear (Edge voice only; the browser voice needs no download). */
export function prefetchSpeech(texts: string[]): void {
  if (typeof window === "undefined") return;
  const settings = getTtsSettings();
  if (settings.engine !== "edge") return;
  for (const text of texts) {
    const clean = text.trim();
    if (!clean) continue;
    const url = ttsUrl(clean, settings);
    if (prefetched.has(url)) continue;
    prefetched.set(
      url,
      limited(() =>
        fetch(url)
          .then((response) => (response.ok ? response.blob() : null))
          .then((blob) => (blob && blob.size > 0 ? URL.createObjectURL(blob) : null))
          .catch(() => null),
      ),
    );
    evictOldest();
  }
}

export function stopSpeaking(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
}

async function playEdge(text: string, settings: TtsSettings): Promise<void> {
  const url = ttsUrl(text, settings);
  const ready = prefetched.get(url);
  const audio = new Audio((ready && (await ready)) || url); // prefetched blob, or still in flight -> wait for it
  stopSpeaking(); // another sound may have started while waiting
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
      await playEdge(clean, settings);
      return;
    } catch {
      // backend or network unavailable -> browser voice
    }
  }
  await speakBrowser(clean, settings);
}
