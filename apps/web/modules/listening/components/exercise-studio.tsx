"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "@/components/ui/toast";
import {
  AlertTriangle,
  Bot,
  Eye,
  EyeOff,
  Mic,
  MicOff,
  Pause,
  Play,
  RotateCcw,
  Sliders,
  Sparkles,
  Volume2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { MicTestDialog } from "@/components/mic-test-dialog";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import { cn } from "@/lib/utils";
import type { DictationCheckResponse, ListeningExercise, ShadowingEvaluateResponse } from "@/types";
import { AnswerStep } from "./answer-step";

const MAX_RECORDING_SECONDS = 60;

const ACCENT_META: Record<string, { label: string; flag: string; tone: string }> = {
  US: { label: "Mỹ (General American)", flag: "🇺🇸", tone: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800" },
  UK: { label: "Anh (Received Pronunciation)", flag: "🇬🇧", tone: "bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:border-rose-800" },
  AU: { label: "Úc (Australian English)", flag: "🇦🇺", tone: "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800" },
  CA: { label: "Canada (Canadian English)", flag: "🇨🇦", tone: "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800" },
};

interface ExerciseStudioProps {
  exercise: ListeningExercise;
  mode: "dictation" | "shadowing";
}

export function ExerciseStudio({ exercise, mode }: ExerciseStudioProps) {
  // Audio state
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Dictation state (auto-reset when exercise changes via key)
  const [learnerInput, setLearnerInput] = useState("");
  const [checking, setChecking] = useState(false);
  const [diffResult, setDiffResult] = useState<DictationCheckResponse | null>(null);
  const [showFullTranscript, setShowFullTranscript] = useState(false);

  // Shadowing & Mic Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const [recordedAudioBase64, setRecordedAudioBase64] = useState<string | null>(null);
  const [userTranscript, setUserTranscript] = useState<string>("");
  const [evaluatingAi, setEvaluatingAi] = useState(false);
  const [aiEvaluation, setAiEvaluation] = useState<ShadowingEvaluateResponse | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<number | null>(null);
  const userAudioRef = useRef<HTMLAudioElement | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const [isPlayingUserAudio, setIsPlayingUserAudio] = useState(false);
  const [shadowingTranscriptVisible, setShadowingTranscriptVisible] = useState(false);
  const [micTestOpen, setMicTestOpen] = useState(false);

  // Clean up native and user audio instances on unmount / exercise change
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
        audioRef.current = null;
      }
      if (userAudioRef.current) {
        userAudioRef.current.pause();
        userAudioRef.current.src = "";
        userAudioRef.current = null;
      }
      // Leaving the exercise while recording must release the microphone and recognition.
      if (recordingTimerRef.current) window.clearInterval(recordingTimerRef.current);
      try {
        recognitionRef.current?.stop();
      } catch {
        // already stopped
      }
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.onstop = null;
        mediaRecorderRef.current.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => () => {
    if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
  }, [recordedAudioUrl]);

  const getAudioUrl = useCallback((sentence: string, voice: string) => {
    return `/api/tts?text=${encodeURIComponent(sentence)}&voice=${encodeURIComponent(voice)}&rate=${encodeURIComponent("+0%")}`;
  }, []);

  const playNativeAudio = useCallback(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.playbackRate = playbackSpeed;
        audioRef.current.play().then(
          () => setIsPlaying(true),
          () => setIsPlaying(false),
        );
      }
      return;
    }

    const audioUrl = exercise.audio_url || getAudioUrl(exercise.sentence, exercise.voice);
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    audio.playbackRate = playbackSpeed;
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => {
      setIsPlaying(false);
      toast.add({ title: "Không phát được âm thanh", description: "Lỗi kết nối tới file audio ETS hoặc giọng đọc bản xứ", type: "error" });
    };
    audio.play().then(
      () => setIsPlaying(true),
      () => setIsPlaying(false),
    );
  }, [exercise.audio_url, exercise.sentence, exercise.voice, getAudioUrl, isPlaying, playbackSpeed]);

  const replayNativeAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.playbackRate = playbackSpeed;
      audioRef.current.play().then(
        () => setIsPlaying(true),
        () => setIsPlaying(false),
      );
    } else {
      playNativeAudio();
    }
  }, [playbackSpeed, playNativeAudio]);

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  };

  const handleCheckDictation = async () => {
    if (!learnerInput.trim()) return;
    setChecking(true);
    try {
      const res = await api<DictationCheckResponse>("/listening/check-dictation", {
        method: "POST",
        json: {
          question_id: exercise.id,
          learner_text: learnerInput.trim(),
          target_transcript: exercise.target_transcript || exercise.sentence,
        },
      });
      setDiffResult(res);
      void refreshLearner();
    } catch (err) {
      alert(errorMessage(err));
    } finally {
      setChecking(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      userAudioRef.current?.pause();
      userAudioRef.current = null; // "Nghe lại giọng của bạn" must play the new take
      setIsPlayingUserAudio(false);
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      setRecordedAudioUrl(null);
      setRecordedAudioBase64(null);
      setUserTranscript("");
      setAiEvaluation(null);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || "audio/webm";
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(url);
        stream.getTracks().forEach((track) => track.stop());

        const reader = new FileReader();
        reader.onloadend = () => {
          const res = reader.result as string;
          if (res) {
            setRecordedAudioBase64(res);
          }
        };
        reader.readAsDataURL(audioBlob);
      };

      if (typeof window !== "undefined") {
        const win = window as unknown as {
          SpeechRecognition?: new () => {
            lang: string;
            continuous: boolean;
            interimResults: boolean;
            maxAlternatives?: number;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onresult: (e: any) => void;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onerror: (e: any) => void;
            start: () => void;
            stop: () => void;
          };
          webkitSpeechRecognition?: new () => {
            lang: string;
            continuous: boolean;
            interimResults: boolean;
            maxAlternatives?: number;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onresult: (e: any) => void;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onerror: (e: any) => void;
            start: () => void;
            stop: () => void;
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
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            recognition.onresult = (e: any) => {
              let fullText = "";
              for (let i = 0; i < e.results.length; ++i) {
                const t = e.results[i]?.[0]?.transcript;
                if (t) fullText += (fullText ? " " : "") + t.trim();
              }
              if (fullText) setUserTranscript(fullText);
            };
            recognition.onerror = (e: unknown) => {
              console.warn("SpeechRecognition error in shadowing:", e);
            };
            recognition.start();
            recognitionRef.current = recognition;
          } catch (e) {
            console.warn("Could not start SpeechRecognition:", e);
          }
        }
      }

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      recordingTimerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev + 1 >= MAX_RECORDING_SECONDS) stopRecordingRef.current();
          return prev + 1;
        });
      }, 1000);
    } catch {
      setMicTestOpen(true);
      toast.add({
        title: "Không thể truy cập microphone",
        description: "Vui lòng cấp quyền truy cập microphone trên thiết bị theo bảng chẩn đoán.",
        type: "error",
      });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordingTimerRef.current) {
        window.clearInterval(recordingTimerRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    }
  };
  const stopRecordingRef = useRef(stopRecording);
  useEffect(() => {
    stopRecordingRef.current = stopRecording;
  });

  const handleEvaluateShadowing = async () => {
    setEvaluatingAi(true);
    try {
      const res = await api<ShadowingEvaluateResponse>("/listening/evaluate-shadowing", {
        method: "POST",
        json: {
          exercise_id: exercise.id,
          target_sentence: exercise.sentence,
          user_transcript: userTranscript || undefined,
          audio_base64: recordedAudioBase64 || undefined,
          phonetic_cues: exercise.phonetic_cues,
          accent: exercise.accent,
        },
      });
      setAiEvaluation(res);
      void refreshLearner();
    } catch (err) {
      alert(errorMessage(err));
    } finally {
      setEvaluatingAi(false);
    }
  };

  const togglePlayUserAudio = () => {
    if (!recordedAudioUrl) return;
    if (userAudioRef.current) {
      if (isPlayingUserAudio) {
        userAudioRef.current.pause();
        setIsPlayingUserAudio(false);
      } else {
        userAudioRef.current.play().then(
          () => setIsPlayingUserAudio(true),
          () => setIsPlayingUserAudio(false),
        );
      }
      return;
    }
    const audio = new Audio(recordedAudioUrl);
    userAudioRef.current = audio;
    audio.onended = () => setIsPlayingUserAudio(false);
    audio.onerror = () => setIsPlayingUserAudio(false);
    audio.play().then(
      () => setIsPlayingUserAudio(true),
      () => setIsPlayingUserAudio(false),
    );
  };

  const accentInfo = ACCENT_META[exercise.accent] ?? ACCENT_META.US;

  return (
    <>
      <Card className="border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs font-semibold text-blue-600 dark:text-blue-400">
              {exercise.test_id} • {exercise.part}
              {exercise.question_no ? ` Q${exercise.question_no}` : ""}
            </Badge>
            {!exercise.audio_url && (
              <Badge className={cn("text-xs font-medium border shrink-0", accentInfo.tone)}>
                <span className="mr-1">{accentInfo.flag}</span>
                <span className="hidden sm:inline">{accentInfo.label}</span>
                <span className="sm:hidden">{exercise.accent}</span>
              </Badge>
            )}
            <Badge variant="secondary" className="capitalize text-xs shrink-0">
              Độ khó: {exercise.difficulty}
            </Badge>
            {exercise.audio_url && (
              <Badge className="bg-amber-500/10 text-amber-700 border-amber-300 dark:border-amber-800 dark:text-amber-400 font-medium text-xs shrink-0 flex items-center gap-1">
                <span>🎧</span>
                <span>ETS Official Audio</span>
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-1">
            <span className="text-[11px] font-medium text-slate-400">Tốc độ:</span>
            {[0.8, 1.0, 1.2].map((s) => (
              <button
                key={s}
                onClick={() => handleSpeedChange(s)}
                className={cn(
                  "rounded px-2 py-0.5 font-mono text-[11px] font-semibold transition-colors",
                  playbackSpeed === s
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400",
                )}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Audio Master Control */}
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-gradient-to-b from-slate-50 to-slate-100/60 p-6 text-center border border-slate-200/80 dark:from-slate-800/40 dark:to-slate-800/80 dark:border-slate-700/60">
          <div className="flex items-center gap-4">
            <Button
              onClick={replayNativeAudio}
              variant="outline"
              size="icon"
              className="h-10 w-10 rounded-full border-slate-300 dark:border-slate-700"
              title="Phát lại từ đầu"
            >
              <RotateCcw className="h-4 w-4 text-slate-600 dark:text-slate-400" />
            </Button>

            <Button
              onClick={playNativeAudio}
              size="icon"
              className="h-16 w-16 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/25 transition-transform active:scale-95"
            >
              {isPlaying ? <Pause className="h-8 w-8" /> : <Play className="h-8 w-8 ml-1" />}
            </Button>

            <Button
              onClick={playNativeAudio}
              variant="outline"
              size="icon"
              className="h-10 w-10 rounded-full border-slate-300 dark:border-slate-700"
              title="Nghe mẫu phát âm"
            >
              <Volume2 className="h-4 w-4 text-slate-600 dark:text-slate-400" />
            </Button>
          </div>

          <div className="text-xs text-slate-500 dark:text-slate-400">
            {exercise.audio_url
              ? "Audio gốc ETS: nghe trọn câu hỏi và các phương án"
              : `Giọng đọc máy (${accentInfo.label}) — câu này chưa có audio gốc`}
          </div>
        </div>

        {/* Part 1 Photograph Display */}
        {exercise.image_url && (
          <div className="flex flex-col items-center justify-center p-4 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2.5 flex items-center gap-1.5 self-start">
              <span>📷</span>
              <span>Hình ảnh Part 1 (ETS Official Photograph)</span>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={exercise.image_url}
              alt={`Part 1 Question ${exercise.question_no ?? ""}`}
              className="max-h-80 w-auto object-contain rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm"
            />
          </div>
        )}

        {/* DICTATION MODE */}
        {mode === "dictation" && (
          <div className="space-y-4">
            {exercise.choice_a && <AnswerStep exercise={exercise} />}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                  Nhập văn bản bạn nghe được:
                </label>
                <span className="font-mono text-xs text-slate-400">
                  {learnerInput.trim() ? `${learnerInput.trim().split(/\s+/).length} từ` : "0 từ"}
                </span>
              </div>
              <Textarea
                value={learnerInput}
                onChange={(e) => setLearnerInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    void handleCheckDictation();
                  }
                }}
                placeholder="Lắng nghe âm thanh và gõ lại toàn bộ câu... (bấm Ctrl + Enter để kiểm tra)"
                rows={3}
                className="font-mono text-sm leading-relaxed border-slate-300 focus:border-blue-500 dark:border-slate-700"
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 self-start p-0 sm:px-2"
                onClick={() => setShowFullTranscript(!showFullTranscript)}
              >
                {showFullTranscript ? <EyeOff className="h-3.5 w-3.5 mr-1" /> : <Eye className="h-3.5 w-3.5 mr-1" />}
                {showFullTranscript ? "Ẩn đáp án gốc" : "Xem trước đáp án gốc"}
              </Button>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 sm:flex-none"
                  onClick={() => {
                    setLearnerInput("");
                    setDiffResult(null);
                  }}
                  disabled={!learnerInput}
                >
                  Xóa
                </Button>
                <Button
                  onClick={handleCheckDictation}
                  disabled={checking || !learnerInput.trim()}
                  size="sm"
                  className="flex-2 sm:flex-none bg-blue-600 hover:bg-blue-700 text-white font-semibold"
                >
                  {checking ? "Đang so khớp..." : "Kiểm Tra Chính Tả"}
                </Button>
              </div>
            </div>

            {showFullTranscript && !diffResult && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-850 dark:text-slate-300">
                <span className="text-xs font-semibold text-slate-400 block mb-1 uppercase">Văn bản gốc:</span>
                {exercise.target_transcript || exercise.sentence}
              </div>
            )}

            {/* Diff & Phonetics Result */}
            {diffResult && (
              <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50/70 p-5 dark:border-slate-800 dark:bg-slate-900/90">
                <div className="flex items-center justify-between border-b border-slate-200 pb-4 dark:border-slate-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-black text-slate-900 dark:text-slate-100">
                        {diffResult.accuracy}%
                      </span>
                      <Badge
                        className={cn(
                          "text-xs font-bold",
                          diffResult.accuracy >= 95
                            ? "bg-emerald-600 text-white"
                            : diffResult.accuracy >= 70
                              ? "bg-blue-600 text-white"
                              : "bg-amber-600 text-white",
                        )}
                      >
                        {diffResult.accuracy >= 95
                          ? "Xuất sắc (Perfect)"
                          : diffResult.accuracy >= 70
                            ? "Khá tốt (Good)"
                            : "Cần cải thiện (Needs Review)"}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500">
                      Chính xác: {diffResult.correct_words} / {diffResult.total_words} từ
                    </p>
                  </div>

                  <Progress value={diffResult.accuracy} className="h-2.5 w-32 bg-slate-200 dark:bg-slate-700" />
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-semibold uppercase text-slate-500">So khớp từng từ (Word Diff):</span>
                  <div className="flex flex-wrap items-center gap-2 rounded-xl bg-white p-4 font-mono text-sm leading-loose border border-slate-200 dark:bg-slate-950 dark:border-slate-800">
                    {diffResult.tokens.map((t, idx) => {
                      if (t.status === "correct") {
                        return (
                          <span
                            key={idx}
                            className="rounded bg-emerald-50 px-2 py-0.5 font-bold text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800"
                            title="Chính xác"
                          >
                            {t.word}
                          </span>
                        );
                      }
                      if (t.status === "misspelled") {
                        return (
                          <span
                            key={idx}
                            className="inline-flex flex-col rounded bg-rose-50 px-2 py-0.5 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800"
                            title={`Bạn gõ: ${t.learner_word || "trống"}`}
                          >
                            <span className="line-through opacity-70 text-[10px]">{t.learner_word}</span>
                            <span className="font-bold">{t.word}</span>
                          </span>
                        );
                      }
                      if (t.status === "missing") {
                        return (
                          <span
                            key={idx}
                            className="rounded bg-amber-50 px-2 py-0.5 font-bold text-amber-700 border border-dashed border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800"
                            title="Từ bị thiếu (bạn chưa gõ)"
                          >
                            [{t.word}]
                          </span>
                        );
                      }
                      return (
                        <span
                          key={idx}
                          className="rounded bg-purple-50 px-2 py-0.5 line-through text-purple-700 border border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800"
                          title="Từ thừa (không có trong câu gốc)"
                        >
                          {t.learner_word}
                        </span>
                      );
                    })}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-1">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Đúng (Correct)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> Sai chính tả (Misspelled)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> Thiếu từ (Missing)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-purple-500" /> Gõ thừa (Extra)
                  </span>
                </div>

                {diffResult.phonetic_cues && diffResult.phonetic_cues.length > 0 && (
                  <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-900/50 dark:bg-indigo-950/20">
                    <div className="flex items-center gap-2 mb-2 font-semibold text-xs text-indigo-900 dark:text-indigo-300 uppercase tracking-wider">
                      <Sparkles className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                      Hiện tượng ngữ âm thực chiến (Connected Speech Analysis):
                    </div>
                    <ul className="space-y-1 text-xs text-indigo-950 dark:text-indigo-200 list-disc list-inside">
                      {diffResult.phonetic_cues.map((cue, cIdx) => (
                        <li key={cIdx}>{cue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(exercise.explanation || exercise.paraphrase_pair) && (
                  <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2 dark:border-slate-800 dark:bg-slate-950 text-xs">
                    {exercise.explanation && (
                      <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-0.5">
                          Giải thích chi tiết & ngữ cảnh:
                        </span>
                        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">{exercise.explanation}</p>
                      </div>
                    )}
                    {exercise.distractor_analysis && (
                      <div>
                        <span className="font-semibold text-rose-700 dark:text-rose-400 block mb-0.5">
                          Bẫy thường gặp (Distractor Trap):
                        </span>
                        <p className="text-slate-600 dark:text-slate-400 leading-relaxed">{exercise.distractor_analysis}</p>
                      </div>
                    )}
                    {exercise.paraphrase_pair && (
                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                        <span className="font-semibold text-blue-700 dark:text-blue-400">
                          Cặp từ đồng nghĩa (Paraphrase Vault):{" "}
                        </span>
                        <span className="font-mono text-slate-700 dark:text-slate-300">{exercise.paraphrase_pair}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* SHADOWING MODE */}
        {mode === "shadowing" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-3 dark:border-blue-900/40 dark:bg-blue-950/20">
                <span className="font-bold text-blue-800 dark:text-blue-300 block mb-1">Bước 1: Nghe ngấm</span>
                <p className="text-slate-600 dark:text-slate-400 leading-normal">
                  Nghe 2-3 lần để cảm nhận ngữ điệu, trọng âm từ và điểm ngắt nghỉ của người bản xứ.
                </p>
              </div>
              <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-3 dark:border-indigo-900/40 dark:bg-indigo-950/20">
                <span className="font-bold text-indigo-800 dark:text-indigo-300 block mb-1">Bước 2: Nói nhại (Shadow)</span>
                <p className="text-slate-600 dark:text-slate-400 leading-normal">
                  Bấm nút micro và nói đuổi theo ngay sau loa với độ trễ khoảng 0.5 - 1 giây.
                </p>
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 dark:border-emerald-900/40 dark:bg-emerald-950/20">
                <span className="font-bold text-emerald-800 dark:text-emerald-300 block mb-1">Bước 3: AI Chấm điểm & Đối chiếu</span>
                <p className="text-slate-600 dark:text-slate-400 leading-normal">
                  Nghe lại bản thu và để AI đóng vai trò giám khảo khách quan chấm điểm & chỉ ra lỗi phát âm.
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 space-y-3 dark:border-slate-800 dark:bg-slate-900/90">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                  Lời thoại mẫu (Script):
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400"
                  onClick={() => setShadowingTranscriptVisible(!shadowingTranscriptVisible)}
                >
                  {shadowingTranscriptVisible ? (
                    <EyeOff className="h-3.5 w-3.5 mr-1" />
                  ) : (
                    <Eye className="h-3.5 w-3.5 mr-1" />
                  )}
                  {shadowingTranscriptVisible ? "Làm mờ lời thoại (Tăng độ khó)" : "Hiện lời thoại"}
                </Button>
              </div>

              <div
                className={cn(
                  "rounded-xl bg-white p-4 border border-slate-200 dark:bg-slate-950 dark:border-slate-800 transition-all",
                  !shadowingTranscriptVisible && "blur-md select-none filter opacity-40",
                )}
              >
                <div className="font-mono text-base leading-relaxed text-slate-900 dark:text-slate-100">
                  {exercise.sentence}
                </div>
              </div>

              {exercise.phonetic_cues && exercise.phonetic_cues.length > 0 && (
                <div className="text-xs text-indigo-700 dark:text-indigo-300 bg-indigo-50/50 dark:bg-indigo-950/30 p-3 rounded-lg border border-indigo-100 dark:border-indigo-900/40">
                  <span className="font-semibold">Lưu ý ngữ âm khi nhại: </span>
                  {exercise.phonetic_cues.join(" ")}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900 text-center space-y-4">
              <div className="flex flex-col items-center justify-center gap-3">
                {isRecording ? (
                  <Button
                    onClick={stopRecording}
                    size="lg"
                    className="h-16 w-16 rounded-full bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-500/30 animate-pulse"
                  >
                    <MicOff className="h-8 w-8" />
                  </Button>
                ) : (
                  <Button
                    onClick={startRecording}
                    size="lg"
                    className="h-16 w-16 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/25"
                  >
                    <Mic className="h-8 w-8" />
                  </Button>
                )}

                <div>
                  <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    {isRecording ? `Đang thu âm: ${recordingSeconds}s (bấm lại để dừng)` : "Bấm Micro để bắt đầu nói nhại"}
                  </p>
                  <p className="text-xs text-slate-500">
                    {isRecording ? "Nói nhại đồng thời theo băng hoặc ngay sau băng" : "Yêu cầu quyền truy cập micro từ trình duyệt"}
                  </p>
                </div>

                {!isRecording && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setMicTestOpen(true)}
                    className="h-7 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/40 gap-1.5 cursor-pointer"
                  >
                    <Sliders className="h-3.5 w-3.5" />
                    <span>Kiểm tra Micro & Quyền thiết bị</span>
                  </Button>
                )}
              </div>

              {recordedAudioUrl && (
                <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    <Button
                      onClick={togglePlayUserAudio}
                      variant="outline"
                      size="sm"
                      className="flex items-center gap-2 border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-700 dark:text-emerald-300"
                    >
                      {isPlayingUserAudio ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      <span>{isPlayingUserAudio ? "Dừng bản thu" : "Nghe lại giọng của bạn"}</span>
                    </Button>

                    <Button
                      onClick={playNativeAudio}
                      variant="outline"
                      size="sm"
                      className="flex items-center gap-2 border-blue-300 text-blue-700 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-300"
                    >
                      <Volume2 className="h-4 w-4" />
                      <span>Nghe lại giọng bản xứ</span>
                    </Button>

                    <Button
                      onClick={handleEvaluateShadowing}
                      disabled={evaluatingAi}
                      size="sm"
                      className="flex items-center gap-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 text-white font-bold shadow-md shadow-blue-500/25 hover:opacity-95"
                    >
                      <Bot className="h-4 w-4" />
                      <span>{evaluatingAi ? "Giám khảo AI đang chấm điểm..." : "Chấm Điểm & Hướng Dẫn AI"}</span>
                    </Button>
                  </div>

                  <div className="max-w-lg mx-auto space-y-2 pt-1">
                    {userTranscript ? (
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3 text-left dark:border-emerald-900/50 dark:bg-emerald-950/30 text-xs">
                        <span className="mb-1.5 flex items-center gap-1.5 font-bold text-emerald-800 dark:text-emerald-300">
                          <Sparkles className="h-3.5 w-3.5" />
                          <span>Giọng nói nhận diện được:</span>
                        </span>
                        <p className="rounded-lg border border-emerald-300 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-800 dark:border-emerald-700 dark:bg-slate-900 dark:text-slate-200">
                          {userTranscript}
                        </p>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-left dark:border-amber-900/50 dark:bg-amber-950/20 text-xs">
                        <div className="flex items-start gap-2 text-amber-800 dark:text-amber-200">
                          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                          <p className="flex-1 text-[11px] leading-relaxed">
                            Đã lưu bản thu ({recordingSeconds}s). Trình duyệt chưa chuyển giọng nói thành chữ (thường gặp trên Opera / iOS / PWA), nên chỉ AI nghe trực tiếp bản thu mới chấm được điểm. Nếu không, bạn vẫn nhận hướng dẫn ngữ âm và có thể tự so bản thu với giọng gốc.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* AI EVALUATION SCORECARD */}
            {aiEvaluation && (
              <div className="rounded-2xl border border-blue-200 bg-gradient-to-b from-blue-50/40 via-white to-slate-50 p-6 space-y-6 shadow-sm dark:border-blue-900/50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950">
                {aiEvaluation.overall_score === null ? (
                  <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-900 dark:text-amber-200">
                    <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
                    <div className="space-y-1">
                      <p className="font-bold">Chưa chấm điểm</p>
                      <p className="text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">
                        Không có văn bản nhận dạng giọng nói và chưa có AI nghe trực tiếp bản thu, nên hệ thống không đưa ra điểm. Phần nhận xét ngữ âm bên dưới vẫn áp dụng cho câu này.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                  {/* Header with Scores */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5 dark:border-slate-800">
                    <div className="flex items-center gap-4">
                      <div
                        className={cn(
                          "flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl font-black text-2xl shadow-lg",
                          aiEvaluation.overall_score >= 85
                            ? "bg-emerald-600 text-white shadow-emerald-500/30"
                            : aiEvaluation.overall_score >= 70
                              ? "bg-blue-600 text-white shadow-blue-500/30"
                              : "bg-amber-600 text-white shadow-amber-500/30",
                        )}
                      >
                        {aiEvaluation.overall_score}%
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge
                            className={cn(
                              "text-xs font-bold",
                              aiEvaluation.overall_score >= 85
                                ? "bg-emerald-600 text-white"
                                : aiEvaluation.overall_score >= 70
                                  ? "bg-blue-600 text-white"
                                  : "bg-amber-600 text-white",
                            )}
                          >
                            {aiEvaluation.verdict}
                          </Badge>
                          {aiEvaluation.analysis_mode === "audio_multimodal" ? (
                            <Badge className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-[11px] font-bold flex items-center gap-1 shadow-xs">
                              <Sparkles className="h-3 w-3" />
                              <span>Gemini Multimodal • Sóng âm gốc</span>
                            </Badge>
                          ) : (
                            <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                              AI Examiner • {aiEvaluation.provider}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                          {aiEvaluation.analysis_mode === "audio_multimodal"
                            ? "Giám khảo Gemini đã nghe trực tiếp file ghi âm từ micro của bạn để chấm điểm ngữ âm thực tế."
                            : "Đánh giá dựa trên đối soát âm vị, độ ngắt nghỉ và hiện tượng nối âm thực chiến."}
                        </p>
                      </div>
                    </div>

                    {/* Sub Scores */}
                    <div className="grid grid-cols-2 gap-3 min-w-[220px]">
                      <div className="rounded-xl border border-slate-200 bg-white/80 p-2.5 text-center dark:border-slate-800 dark:bg-slate-850">
                        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                          Độ chuẩn từ (Accuracy)
                        </span>
                        <span className="font-black text-lg text-slate-800 dark:text-slate-100">
                          {aiEvaluation.accuracy_score}%
                        </span>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white/80 p-2.5 text-center dark:border-slate-800 dark:bg-slate-850">
                        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                          Độ trôi chảy (Fluency)
                        </span>
                        <span className="font-black text-lg text-slate-800 dark:text-slate-100">
                          {aiEvaluation.fluency_score}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Recognized Speech */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span className="font-semibold uppercase tracking-wider">
                        {aiEvaluation.analysis_mode === "audio_multimodal"
                          ? "Gemini nhận diện trực tiếp từ sóng âm micro của bạn:"
                          : "AI nghe được từ giọng đọc của bạn:"}
                      </span>
                      <span className="font-mono text-[11px] text-blue-600 dark:text-blue-400">
                        {aiEvaluation.analysis_mode === "audio_multimodal"
                          ? `Gemini ${aiEvaluation.model || "Flash"} (Raw Audio)`
                          : "Speech Recognition"}
                      </span>
                    </div>
                    <div className="rounded-xl bg-slate-100/80 p-3 font-mono text-sm text-slate-800 italic border border-slate-200 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200">
                      &ldquo;{aiEvaluation.recognized_transcript || "(Chưa bắt được âm thanh rõ ràng)"}&rdquo;
                    </div>
                  </div>

                  {/* Word by Word Breakdown */}
                  <div className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Chi tiết phát âm từng từ (Word Breakdown):
                    </span>
                    <div className="flex flex-wrap gap-2 p-3 bg-white rounded-xl border border-slate-200 dark:bg-slate-950 dark:border-slate-800">
                      {aiEvaluation.words.map((w, idx) => (
                        <div
                          key={idx}
                          className={cn(
                            "group relative px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border cursor-help",
                            w.status === "perfect" &&
                              "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800",
                            w.status === "good" &&
                              "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800",
                            w.status === "needs_work" &&
                              "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800",
                            w.status === "missed" &&
                              "bg-slate-100 text-slate-500 border-slate-200 line-through dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
                          )}
                          title={w.note || w.status}
                        >
                          <span>{w.word}</span>
                          {w.note && (
                            <span className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1 bg-slate-900 text-white text-[10px] rounded-md shadow-lg whitespace-nowrap z-30">
                              {w.note}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center gap-4 text-[11px] text-slate-500 pt-1">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-emerald-500" /> Chuẩn âm
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-blue-500" /> Rõ ràng
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-amber-500" /> Cần chỉnh âm
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-slate-400" /> Nuốt/thiếu từ
                      </span>
                    </div>
                  </div>
                  </>
                )}

                {/* Connected Speech Feedback */}
                {aiEvaluation.connected_speech_feedback && (
                  <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-900/50 dark:bg-indigo-950/20 space-y-1">
                    <span className="text-xs font-bold text-indigo-900 dark:text-indigo-300 uppercase tracking-wider flex items-center gap-2">
                      <Sparkles className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                      Nhận xét hiện tượng ngữ âm tự nhiên:
                    </span>
                    <p className="text-xs text-indigo-950 dark:text-indigo-200 leading-relaxed">
                      {aiEvaluation.connected_speech_feedback}
                    </p>
                  </div>
                )}

                {/* Actionable Coaching Tips */}
                {aiEvaluation.coaching_tips && aiEvaluation.coaching_tips.length > 0 && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 dark:border-amber-900/40 dark:bg-amber-950/20 space-y-2">
                    <span className="text-xs font-bold text-amber-900 dark:text-amber-300 uppercase tracking-wider flex items-center gap-2">
                      💡 Lời khuyên & Hướng dẫn cải thiện từ Giám khảo AI:
                    </span>
                    <ul className="space-y-1.5 text-xs text-amber-950 dark:text-amber-200">
                      {aiEvaluation.coaching_tips.map((tip, tIdx) => (
                        <li key={tIdx} className="flex items-start gap-2">
                          <span className="text-amber-500 font-bold">•</span>
                          <span className="leading-relaxed">{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
    <MicTestDialog open={micTestOpen} onOpenChange={setMicTestOpen} />
    </>
  );
}
