"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Mic,
  RotateCcw,
  Sliders,
  Sparkles,
  Square,
  Volume2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MicTestDialog } from "@/components/mic-test-dialog";
import { api, errorMessage } from "@/lib/api";
import { AudioRecorder } from "@/lib/audio-recorder";
import { speak } from "@/lib/audio";
import { ipa } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { VocabPronounceResponse } from "@/types";

interface PronounceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  word: string;
  expectedIpa?: string | null;
  meaning?: string | null;
}

export function PronounceDialog({
  open,
  onOpenChange,
  word,
  expectedIpa,
  meaning,
}: PronounceDialogProps) {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0);
  const [speechDetected, setSpeechDetected] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<VocabPronounceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [micTestOpen, setMicTestOpen] = useState(false);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const recognitionRef = useRef<{ stop: () => void; abort: () => void } | null>(null);
  const recognizedTextRef = useRef<string>("");
  const isRecordingRef = useRef(false);
  const isStoppingRef = useRef(false);
  const stopRecordingRef = useRef<() => Promise<void>>(async () => {});

  const cleanup = useCallback(() => {
    isRecordingRef.current = false;
    isStoppingRef.current = false;
    if (recorderRef.current?.isRecording()) {
      recorderRef.current.cancel();
    }
    recorderRef.current = null;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (!isRecordingRef.current || isStoppingRef.current) return;
    isStoppingRef.current = true;
    isRecordingRef.current = false;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setRecording(false);
    setAnalyzing(true);
    setError(null);
    setVolume(0);

    // Wait for recognition engine to finalize transcript if not yet received
    const rec = recognitionRef.current;
    if (rec) {
      if (!recognizedTextRef.current) {
        await new Promise<void>((resolve) => {
          const timeout = setTimeout(resolve, 800);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const origResult = (rec as any).onresult;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (rec as any).onresult = (e: any) => {
            origResult?.(e);
            clearTimeout(timeout);
            resolve();
          };
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const origEnd = (rec as any).onend;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (rec as any).onend = () => {
            origEnd?.();
            clearTimeout(timeout);
            resolve();
          };
          try {
            rec.stop();
          } catch {
            clearTimeout(timeout);
            resolve();
          }
        });
      } else {
        try {
          rec.stop();
        } catch {
          // ignore
        }
      }
      recognitionRef.current = null;
    }

    try {
      let base64 = "";
      if (recorderRef.current) {
        try {
          const res = await recorderRef.current.stop();
          base64 = res.base64;
        } catch {
          // ignore recorder stop error
        }
      }

      const res = await api<VocabPronounceResponse>("/ai/pronounce-vocab", {
        method: "POST",
        json: {
          word: word.trim(),
          expected_ipa: expectedIpa || undefined,
          audio_base64: base64,
          user_transcript: recognizedTextRef.current || undefined,
        },
      });
      setResult(res);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setAnalyzing(false);
      isStoppingRef.current = false;
    }
  }, [word, expectedIpa]);

  useEffect(() => {
    stopRecordingRef.current = stopRecording;
  }, [stopRecording]);

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      cleanup();
      setRecording(false);
      setDuration(0);
      setVolume(0);
      setSpeechDetected(false);
      setLiveTranscript("");
      setAnalyzing(false);
      setResult(null);
      setError(null);
    }
    onOpenChange(nextOpen);
  };

  const startRecording = async () => {
    setError(null);
    setResult(null);
    setSpeechDetected(false);
    setLiveTranscript("");
    setVolume(0);
    recognizedTextRef.current = "";
    cleanup();

    const isIOS = typeof navigator !== "undefined" && /iphone|ipad|ipod/i.test(navigator.userAgent);

    try {
      let hasRecognition = false;
      if (typeof window !== "undefined") {
        const win = window as unknown as {
          SpeechRecognition?: new () => {
            lang: string;
            continuous: boolean;
            interimResults: boolean;
            maxAlternatives: number;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onresult: (e: any) => void;
            onerror: (e: unknown) => void;
            onspeechstart?: () => void;
            onsoundstart?: () => void;
            onspeechend?: () => void;
            start: () => void;
            stop: () => void;
            abort: () => void;
          };
          webkitSpeechRecognition?: new () => {
            lang: string;
            continuous: boolean;
            interimResults: boolean;
            maxAlternatives: number;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onresult: (e: any) => void;
            onerror: (e: unknown) => void;
            onspeechstart?: () => void;
            onsoundstart?: () => void;
            onspeechend?: () => void;
            start: () => void;
            stop: () => void;
            abort: () => void;
          };
        };

        const SpeechRec = win.SpeechRecognition || win.webkitSpeechRecognition;
        if (SpeechRec) {
          try {
            const recognition = new SpeechRec();
            recognition.lang = "en-US";
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.maxAlternatives = 3;

            recognition.onspeechstart = () => {
              setSpeechDetected(true);
            };

            recognition.onsoundstart = () => {
              setSpeechDetected(true);
            };

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            recognition.onresult = (e: any) => {
              let fullText = "";
              for (let i = 0; i < e.results.length; ++i) {
                const t = e.results[i]?.[0]?.transcript;
                if (t) fullText += (fullText ? " " : "") + t.trim();
              }
              if (fullText) {
                recognizedTextRef.current = fullText;
                setLiveTranscript(fullText);
                setSpeechDetected(true);
              }
            };

            recognition.onspeechend = () => {
              setTimeout(() => {
                if (isRecordingRef.current) {
                  void stopRecordingRef.current();
                }
              }, 1200);
            };

            recognition.onerror = (e) => {
              console.warn("SpeechRecognition error:", e);
            };

            recognition.start();
            recognitionRef.current = recognition;
            hasRecognition = true;
          } catch (e) {
            console.warn("Could not start SpeechRecognition:", e);
          }
        }
      }

      // On iOS Safari, getUserMedia and webkitSpeechRecognition conflict over hardware mic access.
      // If SpeechRecognition is available on iOS, let it handle microphone exclusively.
      // On non-iOS devices or when SpeechRecognition is unavailable, use AudioRecorder for volume & audio capture.
      if (!isIOS || !hasRecognition) {
        const recorder = new AudioRecorder({
          autoStopOnSilence: true,
          speechThreshold: 0.035,
          silenceThreshold: 0.02,
          silenceDurationMs: 1800,
          onSpeechDetected: () => {
            setSpeechDetected(true);
          },
          onSilence: () => {
            void stopRecordingRef.current();
          },
          onVolumeChange: (vol) => {
            setVolume(vol);
            if (vol >= 0.04) {
              setSpeechDetected(true);
            }
          },
        });

        recorderRef.current = recorder;
        await recorder.start();
      }

      isRecordingRef.current = true;
      isStoppingRef.current = false;
      setRecording(true);
      setDuration(0);

      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setDuration(elapsed);
        if (isIOS && hasRecognition) {
          // Provide animated volume wave bars on iOS
          setVolume(Math.random() * 0.4 + 0.35);
        }
        if (elapsed >= 5) {
          void stopRecordingRef.current();
        }
      }, 150);
    } catch (err) {
      setError(errorMessage(err));
      setRecording(false);
      isRecordingRef.current = false;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-500 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 60) return "text-amber-500 border-amber-500/30 bg-amber-500/10";
    return "text-red-500 border-red-500/30 bg-red-500/10";
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md p-6">
        <DialogHeader className="flex flex-row items-center justify-between space-y-0 pb-1">
          <DialogTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
            <Sparkles className="h-4 w-4 text-blue-500" />
            Luyện Phát Âm AI (Multimodal Audio)
          </DialogTitle>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setMicTestOpen(true)}
            className="h-7 cursor-pointer gap-1 px-2 text-xs text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/40"
            title="Kiểm tra Micro & Cấp quyền"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Test Mic</span>
          </Button>
        </DialogHeader>

        {/* Word card header */}
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-center dark:border-slate-800 dark:bg-slate-900/60">
          <div className="flex items-center justify-center gap-3">
            <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">
              {word}
            </h2>
            <button
              type="button"
              onClick={() => void speak(word)}
              className="cursor-pointer rounded-full p-2 text-slate-500 transition hover:bg-slate-200 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-blue-400"
              aria-label="Nghe phát âm chuẩn"
              title="Nghe phát âm chuẩn"
            >
              <Volume2 className="h-5 w-5" />
            </button>
          </div>
          {expectedIpa && (
            <p className="mt-1 font-mono text-sm text-slate-500 dark:text-slate-400">
              {ipa(expectedIpa)}
            </p>
          )}
          {meaning && (
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
              {meaning}
            </p>
          )}
        </div>

        {/* Recording / Action Section */}
        <div className="flex flex-col items-center justify-center gap-4 py-3">
          {error && (
            <div className="flex flex-col gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-600 dark:text-red-400 w-full">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setMicTestOpen(true)}
                className="self-start h-7 cursor-pointer text-xs border-red-300 bg-white/80 hover:bg-white text-red-700 dark:border-red-800 dark:bg-slate-900 dark:text-red-300 gap-1.5"
              >
                <Sliders className="h-3 w-3" /> Kiểm tra Micro & Cấp quyền
              </Button>
            </div>
          )}

          {analyzing ? (
            <div className="flex flex-col items-center gap-2 py-4 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                AI đang phân tích sóng âm thanh của bạn...
              </p>
              <p className="text-xs text-slate-400">
                Chấm điểm nguyên âm, âm đuôi và so sánh phổ tần số IPA
              </p>
            </div>
          ) : recording ? (
            <div className="flex flex-col items-center gap-3 py-2">
              <div className="relative flex items-center justify-center">
                {/* Volume-reactive pulse ring */}
                <span
                  className="absolute rounded-full bg-red-500/30 transition-all duration-75"
                  style={{
                    width: `${Math.max(64, 64 + volume * 80)}px`,
                    height: `${Math.max(64, 64 + volume * 80)}px`,
                    opacity: volume > 0.05 ? 0.6 : 0.2,
                  }}
                />
                <Button
                  size="lg"
                  variant="destructive"
                  onClick={() => void stopRecordingRef.current()}
                  className="relative z-10 h-16 w-16 cursor-pointer rounded-full p-0 shadow-lg shadow-red-500/30 transition-transform active:scale-95"
                  aria-label="Dừng thu âm và nhận xét"
                  title="Nhấn để dừng và nhận kết quả ngay"
                >
                  <Square className="h-6 w-6" />
                </Button>
              </div>

              {/* Realtime audio wave bar visualizer */}
              <div className="flex items-center gap-1 h-6">
                {[0.2, 0.4, 0.7, 1.0, 0.7, 0.4, 0.2].map((factor, i) => (
                  <span
                    key={i}
                    className="w-1 rounded-full bg-red-500 transition-all duration-75"
                    style={{
                      height: `${Math.max(4, volume * factor * 24)}px`,
                      opacity: volume > 0.05 ? 0.9 : 0.3,
                    }}
                  />
                ))}
              </div>

              <div className="text-center space-y-1.5 max-w-xs">
                {liveTranscript ? (
                  <div className="rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800 animate-in fade-in">
                    ✨ Đã nghe: &ldquo;{liveTranscript}&rdquo;
                  </div>
                ) : (
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    {speechDetected
                      ? "Đang ghi nhận giọng nói... Bấm nút đỏ hoặc dừng khi nói xong"
                      : "Đang lắng nghe... Hãy phát âm từ trên"}
                  </p>
                )}
                <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400">
                  <span>{duration}s / 5s</span>
                  <span>•</span>
                  <span>Bấm nút đỏ để hoàn thành</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-1">
              <Button
                size="lg"
                onClick={() => void startRecording()}
                className="h-14 cursor-pointer gap-2 rounded-full px-6 shadow-md hover:shadow-lg transition active:scale-95"
              >
                <Mic className="h-5 w-5 text-white" />
                <span>{result ? "Thu âm lại" : "Nhấn để phát âm"}</span>
              </Button>
              <div className="flex flex-col items-center gap-1 text-center">
                <p className="text-[11px] text-slate-400">
                  Tự động nhận diện dứt lời hoặc tự dừng sau 5s
                </p>
                <button
                  type="button"
                  onClick={() => setMicTestOpen(true)}
                  className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 dark:text-blue-400 hover:underline cursor-pointer"
                >
                  <Sliders className="h-3 w-3" />
                  <span>Micro không nhận tiếng? Bấm kiểm tra</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Results Analysis */}
        {result && !analyzing && !recording && (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/50 p-4 text-xs dark:border-slate-800 dark:bg-slate-900/40 animate-in fade-in duration-200">
            {/* Score header */}
            <div className="flex items-center justify-between border-b border-slate-200 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                {result.is_accurate ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-amber-500" />
                )}
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {result.is_accurate ? "Phát âm chuẩn xác!" : "Cần điều chỉnh thêm"}
                </span>
              </div>
              <div
                className={cn(
                  "rounded-full border px-3 py-1 font-mono text-sm font-black",
                  getScoreColor(result.score),
                )}
              >
                {result.score}%
              </div>
            </div>

            {/* IPA Comparison */}
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="rounded-lg bg-white p-2 border border-slate-200 dark:bg-slate-800/60 dark:border-slate-700/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">
                  Chuẩn kỳ vọng
                </span>
                <p className="mt-0.5 font-mono font-bold text-blue-600 dark:text-blue-400">
                  {result.expected_ipa}
                </p>
              </div>
              <div className="rounded-lg bg-white p-2 border border-slate-200 dark:bg-slate-800/60 dark:border-slate-700/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">
                  Bạn thực tế đọc
                </span>
                <p className="mt-0.5 font-mono font-bold text-purple-600 dark:text-purple-400">
                  {result.recognized_ipa}
                </p>
              </div>
            </div>

            {/* Detailed Feedback Breakdown */}
            <div className="space-y-2 pt-1 text-slate-600 dark:text-slate-300">
              <div>
                <strong className="text-blue-500">🗣️ Nguyên âm: </strong>
                {result.feedback.vowels}
              </div>
              <div>
                <strong className="text-emerald-500">🎯 Phụ âm & Âm đuôi: </strong>
                {result.feedback.consonants}
              </div>
              <div>
                <strong className="text-amber-500">⚡ Trọng âm: </strong>
                {result.feedback.stress}
              </div>
              {result.feedback.tips && (
                <div className="rounded-md bg-blue-500/10 p-2 text-blue-700 dark:text-blue-300 border border-blue-500/20">
                  <strong>💡 Lời khuyên: </strong>
                  {result.feedback.tips}
                </div>
              )}
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
              <Button
                size="sm"
                variant="outline"
                onClick={() => void speak(word)}
                className="h-8 cursor-pointer text-xs"
              >
                <Volume2 className="h-3.5 w-3.5 mr-1" /> Nghe lại mẫu
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={() => void startRecording()}
                className="h-8 cursor-pointer text-xs"
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1" /> Thử lại
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
    <MicTestDialog open={micTestOpen} onOpenChange={setMicTestOpen} />
    </>
  );
}
