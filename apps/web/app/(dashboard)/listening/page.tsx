"use client";

import { useCallback, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Headphones,
  Mic,
  MicOff,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Volume2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState, LoadingState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { DictationCheckResponse, ListeningExercise } from "@/types";

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

function ExerciseStudio({ exercise, mode }: ExerciseStudioProps) {
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
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<number | null>(null);
  const userAudioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlayingUserAudio, setIsPlayingUserAudio] = useState(false);
  const [shadowingTranscriptVisible, setShadowingTranscriptVisible] = useState(true);

  // Activity tracking
  const sessionStartTime = useRef<number | null>(null);

  const getAudioUrl = useCallback((sentence: string, voice: string, speed: number) => {
    const ttsRate = speed === 0.8 ? "-20%" : speed === 1.2 ? "+20%" : "+0%";
    return `/api/tts?text=${encodeURIComponent(sentence)}&voice=${encodeURIComponent(voice)}&rate=${encodeURIComponent(ttsRate)}`;
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

    const audioUrl = getAudioUrl(exercise.sentence, exercise.voice, playbackSpeed);
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    audio.playbackRate = playbackSpeed;
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => setIsPlaying(false);
    audio.play().then(
      () => setIsPlaying(true),
      () => setIsPlaying(false),
    );
  }, [exercise.sentence, exercise.voice, getAudioUrl, isPlaying, playbackSpeed]);

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
      const now = Date.now();
      const elapsedSeconds = sessionStartTime.current
        ? Math.max(1, Math.round((now - sessionStartTime.current) / 1000))
        : 20;
      sessionStartTime.current = now;

      const res = await api<DictationCheckResponse>("/listening/check-dictation", {
        method: "POST",
        json: {
          question_id: exercise.id,
          learner_text: learnerInput.trim(),
          target_transcript: exercise.sentence,
          time_spent_seconds: elapsedSeconds,
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
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(url);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      recordingTimerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch {
      alert("Không thể truy cập microphone. Vui lòng cấp quyền micro trên trình duyệt của bạn.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordingTimerRef.current) {
        window.clearInterval(recordingTimerRef.current);
      }
      void api("/listening/track", {
        method: "POST",
        json: { mode: "shadowing", seconds: Math.max(5, recordingSeconds), items: 1 },
      }).then(() => refreshLearner());
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
    <Card className="border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs font-semibold text-blue-600 dark:text-blue-400">
              {exercise.test_id} • {exercise.part}
              {exercise.question_no ? ` Q${exercise.question_no}` : ""}
            </Badge>
            <Badge className={cn("text-xs font-medium border", accentInfo.tone)}>
              <span className="mr-1">{accentInfo.flag}</span>
              {accentInfo.label}
            </Badge>
            <Badge variant="secondary" className="capitalize text-xs">
              Độ khó: {exercise.difficulty}
            </Badge>
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
            Lắng nghe ngữ điệu và trọng âm câu với giọng bản ngữ {accentInfo.label}
          </div>
        </div>

        {/* DICTATION MODE */}
        {mode === "dictation" && (
          <div className="space-y-4">
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
                onChange={(e) => {
                  setLearnerInput(e.target.value);
                  if (!sessionStartTime.current) sessionStartTime.current = Date.now();
                }}
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

            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400"
                onClick={() => setShowFullTranscript(!showFullTranscript)}
              >
                {showFullTranscript ? <EyeOff className="h-3.5 w-3.5 mr-1" /> : <Eye className="h-3.5 w-3.5 mr-1" />}
                {showFullTranscript ? "Ẩn đáp án gốc" : "Xem trước đáp án gốc (Peek)"}
              </Button>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
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
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold"
                >
                  {checking ? "Đang so khớp..." : "Kiểm Tra Chính Tả (Diff)"}
                </Button>
              </div>
            </div>

            {showFullTranscript && !diffResult && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-850 dark:text-slate-300">
                <span className="text-xs font-semibold text-slate-400 block mb-1 uppercase">Văn bản gốc:</span>
                {exercise.sentence}
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
                <span className="font-bold text-emerald-800 dark:text-emerald-300 block mb-1">Bước 3: Đối chiếu</span>
                <p className="text-slate-600 dark:text-slate-400 leading-normal">
                  Nghe lại bản thu của chính bạn và so sánh độ trôi chảy với giọng bản ngữ.
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
                  {shadowingTranscriptVisible ? "Ẩn lời thoại (Tăng độ khó)" : "Hiện lời thoại"}
                </Button>
              </div>

              <div
                className={cn(
                  "rounded-xl bg-white p-4 font-mono text-base leading-relaxed border border-slate-200 dark:bg-slate-950 dark:border-slate-800 transition-all",
                  !shadowingTranscriptVisible && "blur-xs select-none filter opacity-40",
                )}
              >
                {exercise.sentence}
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
              </div>

              {recordedAudioUrl && (
                <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-center gap-4">
                  <Button
                    onClick={togglePlayUserAudio}
                    variant="outline"
                    className="flex items-center gap-2 border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-700 dark:text-emerald-300"
                  >
                    {isPlayingUserAudio ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                    <span>{isPlayingUserAudio ? "Dừng bản thu" : "Nghe lại giọng của bạn"}</span>
                  </Button>

                  <Button
                    onClick={playNativeAudio}
                    variant="outline"
                    className="flex items-center gap-2 border-blue-300 text-blue-700 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-300"
                  >
                    <Volume2 className="h-4 w-4" />
                    <span>Nghe lại giọng bản xứ</span>
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ListeningStudioPage() {
  const { data: exercises, error, loading, reload } = useApi<ListeningExercise[]>("/listening/exercises?limit=40");

  const [selectedPart, setSelectedPart] = useState<string>("all");
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [mode, setMode] = useState<"dictation" | "shadowing">("dictation");

  const filteredExercises = (exercises ?? []).filter((ex) => {
    if (selectedPart !== "all" && ex.part !== selectedPart) return false;
    return true;
  });

  const currentExercise = filteredExercises[currentIndex];

  const handleNext = () => {
    if (currentIndex < filteredExercises.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  if (loading) {
    return <LoadingState label="Đang tải dữ liệu bài nghe ETS và giọng đọc bản xứ..." />;
  }

  if (error && (!exercises || exercises.length === 0)) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20">
              <Headphones className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Phòng Luyện Nghe (Listening Studio)</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Luyện chép chính tả (Dictation) & Nói nhại (Shadowing) theo chuẩn 4 giọng đọc ETS (Mỹ, Anh, Úc, Canada)
              </p>
            </div>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="flex items-center gap-2">
          <Tabs value={mode} onValueChange={(v) => setMode(v as "dictation" | "shadowing")}>
            <TabsList className="bg-slate-100 dark:bg-slate-800">
              <TabsTrigger value="dictation" className="flex items-center gap-1.5 text-xs font-medium">
                <BookOpen className="h-3.5 w-3.5" />
                Chép Chính Tả (Dictation)
              </TabsTrigger>
              <TabsTrigger value="shadowing" className="flex items-center gap-1.5 text-xs font-medium">
                <Mic className="h-3.5 w-3.5" />
                Nói Nhại (Shadowing)
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
          <span className="mr-1 font-semibold text-slate-500 uppercase">Phần thi:</span>
          {["all", "Part 1", "Part 2", "Part 3"].map((p) => (
            <Button
              key={p}
              variant={selectedPart === p ? "default" : "outline"}
              size="sm"
              className={cn("h-7 px-3 text-xs font-medium", selectedPart === p ? "bg-blue-600 text-white" : "")}
              onClick={() => {
                setSelectedPart(p);
                setCurrentIndex(0);
              }}
            >
              {p === "all" ? "Tất cả các Part" : p}
            </Button>
          ))}
        </div>

        {/* Counter and Navigation */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-slate-500">
            {filteredExercises.length > 0 ? `Câu ${currentIndex + 1} / ${filteredExercises.length}` : "Không có câu hỏi"}
          </span>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" className="h-7 w-7 p-0" onClick={handlePrev} disabled={currentIndex === 0}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={handleNext}
              disabled={currentIndex >= filteredExercises.length - 1}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Studio Area */}
      {currentExercise ? (
        <div className="space-y-6">
          <ExerciseStudio key={currentExercise.id} exercise={currentExercise} mode={mode} />

          {/* Bottom Action Bar */}
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-xs dark:border-slate-800 dark:bg-slate-900">
            <Button variant="outline" size="sm" onClick={handlePrev} disabled={currentIndex === 0}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Câu trước
            </Button>

            <span className="text-xs text-slate-500">
              {currentExercise.part} • Bài {currentIndex + 1} trên {filteredExercises.length}
            </span>

            <Button
              variant="default"
              size="sm"
              onClick={handleNext}
              disabled={currentIndex >= filteredExercises.length - 1}
              className="bg-blue-600 text-white hover:bg-blue-700"
            >
              Câu tiếp theo
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
          </div>
        </div>
      ) : (
        <Card className="p-8 text-center border-dashed">
          <p className="text-sm text-slate-500">Không tìm thấy bài nghe phù hợp với bộ lọc hiện tại.</p>
        </Card>
      )}
    </div>
  );
}
