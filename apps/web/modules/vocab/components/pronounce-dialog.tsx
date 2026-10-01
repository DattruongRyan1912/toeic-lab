"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Mic,
  RotateCcw,
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
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<VocabPronounceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const cleanup = () => {
    if (recorderRef.current?.isRecording()) {
      recorderRef.current.cancel();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      cleanup();
      setRecording(false);
      setDuration(0);
      setAnalyzing(false);
      setResult(null);
      setError(null);
    }
    onOpenChange(nextOpen);
  };

  const stopRecording = async () => {
    if (!recorderRef.current || !recording) return;
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRecording(false);
    setAnalyzing(true);
    setError(null);

    try {
      const { base64 } = await recorderRef.current.stop();
      const res = await api<VocabPronounceResponse>("/ai/pronounce-vocab", {
        method: "POST",
        json: {
          word: word.trim(),
          expected_ipa: expectedIpa || undefined,
          audio_base64: base64,
        },
      });
      setResult(res);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const startRecording = async () => {
    setError(null);
    setResult(null);
    try {
      const recorder = new AudioRecorder();
      recorderRef.current = recorder;
      await recorder.start();
      setRecording(true);
      setDuration(0);

      timerRef.current = setInterval(() => {
        setDuration((prev) => {
          if (prev >= 4) {
            void stopRecording();
            return 5;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      setError(errorMessage(err));
      setRecording(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-500 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 60) return "text-amber-500 border-amber-500/30 bg-amber-500/10";
    return "text-red-500 border-red-500/30 bg-red-500/10";
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
            <Sparkles className="h-4 w-4 text-blue-500" />
            Luyện Phát Âm AI (Multimodal Audio)
          </DialogTitle>
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
            <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {analyzing ? (
            <div className="flex flex-col items-center gap-2 py-4 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                Gemini đang phân tích sóng âm thanh của bạn...
              </p>
            </div>
          ) : recording ? (
            <div className="flex flex-col items-center gap-3 py-2">
              <div className="relative flex items-center justify-center">
                <span className="absolute h-16 w-16 animate-ping rounded-full bg-red-500/40" />
                <Button
                  size="lg"
                  variant="destructive"
                  onClick={() => void stopRecording()}
                  className="h-16 w-16 cursor-pointer rounded-full p-0 shadow-lg shadow-red-500/30"
                  aria-label="Dừng thu âm"
                >
                  <Square className="h-6 w-6" />
                </Button>
              </div>
              <div className="text-center">
                <p className="text-xs font-semibold text-red-500 animate-pulse">
                  Đang thu âm... {duration}s / 5s
                </p>
                <p className="text-[11px] text-slate-400">
                  Hãy nói to rõ ràng từ trên vào micro
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-1">
              <Button
                size="lg"
                onClick={() => void startRecording()}
                className="h-14 cursor-pointer gap-2 rounded-full px-6 shadow-md hover:shadow-lg transition"
              >
                <Mic className="h-5 w-5 text-white" />
                <span>{result ? "Thu âm lại" : "Nhấn để phát âm"}</span>
              </Button>
              <p className="text-[11px] text-slate-400">
                AI sẽ trực tiếp nghe sóng âm để chấm điểm phát âm & âm đuôi
              </p>
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
  );
}
