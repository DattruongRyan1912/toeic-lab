"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bot,
  Briefcase,
  ChevronDown,
  ChevronUp,
  Headphones,
  Laptop,
  Loader2,
  Mic,
  MicOff,
  RotateCcw,
  Send,
  Sparkles,
  Square,
  Volume2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { api, errorMessage, notifyAiQuotaUpdated } from "@/lib/api";
import { AudioRecorder } from "@/lib/audio-recorder";
import { speak, stopSpeaking } from "@/lib/audio";
import { cn } from "@/lib/utils";
import type { VoiceCoachStartResponse, VoiceCoachTurnResponse, VoiceMessage } from "@/types";

interface SpeechRecognitionResultItem {
  transcript: string;
}

interface SpeechRecognitionResultList {
  length: number;
  [index: number]: {
    isFinal: boolean;
    [index: number]: SpeechRecognitionResultItem;
  };
}

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent {
  error: string;
}

interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

interface WindowWithSpeech extends Window {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

const SCENARIOS = [
  {
    id: "business_office",
    title: "Phản xạ Công sở",
    desc: "Lịch họp, đàm phán & quản lý dự án",
    icon: Briefcase,
    color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  },
  {
    id: "tech_interview",
    title: "Phỏng vấn Kỹ sư",
    desc: "Backend, distributed systems & database",
    icon: Laptop,
    color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
  },
  {
    id: "customer_service",
    title: "Xử lý Khiếu nại",
    desc: "Hỗ trợ khách hàng & giải quyết sự cố",
    icon: Headphones,
    color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
  },
  {
    id: "free_conversation",
    title: "Đối thoại Tự do",
    desc: "Trò chuyện cởi mở & sửa phát âm",
    icon: Sparkles,
    color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  },
];

const ACCENTS = [
  { id: "en-US-JennyNeural", label: "Mỹ (US)", flag: "🇺🇸" },
  { id: "en-GB-SoniaNeural", label: "Anh (UK)", flag: "🇬🇧" },
  { id: "en-AU-NatashaNeural", label: "Úc (AU)", flag: "🇦🇺" },
  { id: "en-CA-ClaraNeural", label: "Canada (CA)", flag: "🇨🇦" },
];

export function VoiceStudio() {
  const [scenario, setScenario] = useState("business_office");
  const [accent, setAccent] = useState("en-US-JennyNeural");
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [state, setState] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [transcript, setTranscript] = useState("");
  const [manualText, setManualText] = useState("");
  const [expandedFeedbackId, setExpandedFeedbackId] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"native" | "speech">("native");
  const [nativeDuration, setNativeDuration] = useState(0);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const nativeRecorderRef = useRef<AudioRecorder | null>(null);
  const nativeTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const playAudio = useCallback(
    (audioUrl?: string, text?: string) => {
      stopSpeaking();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setState("speaking");

      const onFinish = () => {
        setState("idle");
      };

      if (audioUrl) {
        const audio = new Audio(audioUrl);
        audioRef.current = audio;
        audio.onended = onFinish;
        audio.onerror = () => {
          // Fallback to browser TTS if Edge TTS fails
          if (text) {
            void speak(text, { voice: accent }).finally(onFinish);
          } else {
            onFinish();
          }
        };
        audio.play().catch(() => {
          // Autoplay policy or playback error
          if (text) {
            void speak(text, { voice: accent }).finally(onFinish);
          } else {
            onFinish();
          }
        });
      } else if (text) {
        void speak(text, { voice: accent }).finally(onFinish);
      } else {
        onFinish();
      }
    },
    [accent],
  );

  const startSession = useCallback(
    (scenarioId: string, accentVoice: string) => {
      setState("thinking");
      api<VoiceCoachStartResponse>("/ai/voice-coach/start", {
        method: "POST",
        json: { scenario: scenarioId, accent: accentVoice },
      })
        .then((res) => {
          const openingMessage: VoiceMessage = {
            id: `ai-${Date.now()}`,
            role: "ai",
            text: res.ai_opening_statement,
            audioUrl: res.audio_url,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          };
          setMessages([openingMessage]);
          playAudio(res.audio_url, res.ai_opening_statement);
        })
        .catch((err: unknown) => {
          toast.add({ title: "Không thể bắt đầu kịch bản", description: errorMessage(err), type: "error" });
          setState("idle");
        });
    },
    [playAudio],
  );

  useEffect(() => {
    let active = true;
    api<VoiceCoachStartResponse>("/ai/voice-coach/start", {
      method: "POST",
      json: { scenario, accent },
    })
      .then((res) => {
        if (!active) return;
        const openingMessage: VoiceMessage = {
          id: `ai-${Date.now()}`,
          role: "ai",
          text: res.ai_opening_statement,
          audioUrl: res.audio_url,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages([openingMessage]);
        playAudio(res.audio_url, res.ai_opening_statement);
      })
      .catch((err: unknown) => {
        if (!active) return;
        toast.add({ title: "Không thể bắt đầu kịch bản", description: errorMessage(err), type: "error" });
        setState("idle");
      });

    return () => {
      active = false;
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (nativeRecorderRef.current?.isRecording()) {
        nativeRecorderRef.current.cancel();
      }
      if (nativeTimerRef.current) {
        clearInterval(nativeTimerRef.current);
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
      stopSpeaking();
    };
  }, [scenario, accent, playAudio]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, transcript]);

  // Submit learner's turn to backend
  const submitTurn = async (spokenText: string) => {
    const clean = spokenText.trim();
    if (!clean) return;

    const userMsgId = `user-${Date.now()}`;
    const userMessage: VoiceMessage = {
      id: userMsgId,
      role: "user",
      text: clean,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setTranscript("");
    setManualText("");
    setState("thinking");

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role === "ai" ? "assistant" : "user",
        content: m.text,
      }));

      const res = await api<VoiceCoachTurnResponse>("/ai/voice-coach/turn", {
        method: "POST",
        json: {
          scenario,
          user_transcript: clean,
          history: historyPayload,
          accent,
        },
      });

      // Update user message with feedback
      setMessages((prev) =>
        prev.map((m) => (m.id === userMsgId ? { ...m, feedback: res.feedback } : m)),
      );
      setExpandedFeedbackId(userMsgId);

      // Add AI reply message
      const aiReply: VoiceMessage = {
        id: `ai-${Date.now()}`,
        role: "ai",
        text: res.spoken_reply,
        audioUrl: res.audio_url,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, aiReply]);
      playAudio(res.audio_url, res.spoken_reply);
      notifyAiQuotaUpdated();
    } catch (err: unknown) {
      toast.add({ title: "Lỗi phản hồi từ AI", description: errorMessage(err), type: "error" });
      setState("idle");
    }
  };

  // Submit learner's raw audio to Gemini Multimodal
  const submitAudioTurn = async (audioBase64: string) => {
    const userMsgId = `user-${Date.now()}`;
    const userMessage: VoiceMessage = {
      id: userMsgId,
      role: "user",
      text: "🎙️ [Đang phân tích sóng âm thanh...]",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setState("thinking");

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role === "ai" ? "assistant" : "user",
        content: m.text,
      }));

      const res = await api<VoiceCoachTurnResponse>("/ai/voice-coach/turn", {
        method: "POST",
        json: {
          scenario,
          audio_base64: audioBase64,
          history: historyPayload,
          accent,
        },
      });

      // Update user message with recognized transcript from Gemini and acoustic feedback
      setMessages((prev) =>
        prev.map((m) =>
          m.id === userMsgId
            ? {
                ...m,
                text: res.user_transcript || "🎙️ [Giọng nói đã ghi âm]",
                feedback: res.feedback,
              }
            : m,
        ),
      );
      setExpandedFeedbackId(userMsgId);

      // Add AI reply message
      const aiReply: VoiceMessage = {
        id: `ai-${Date.now()}`,
        role: "ai",
        text: res.spoken_reply,
        audioUrl: res.audio_url,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, aiReply]);
      playAudio(res.audio_url, res.spoken_reply);
      notifyAiQuotaUpdated();
    } catch (err: unknown) {
      toast.add({ title: "Lỗi phân tích âm thanh từ AI", description: errorMessage(err), type: "error" });
      setState("idle");
    }
  };

  const submitAudioTurnRef = useRef<(b64: string) => Promise<void>>(async () => {});
  useEffect(() => {
    submitAudioTurnRef.current = submitAudioTurn;
  });

  const isNativeRecordingRef = useRef(false);
  const stopNativeRecordingRef = useRef<() => Promise<void>>(async () => {});

  const stopNativeRecording = useCallback(async () => {
    if (!isNativeRecordingRef.current) return;
    isNativeRecordingRef.current = false;

    if (nativeTimerRef.current) {
      clearInterval(nativeTimerRef.current);
      nativeTimerRef.current = null;
    }
    setState("thinking");

    try {
      if (nativeRecorderRef.current) {
        const { base64 } = await nativeRecorderRef.current.stop();
        void submitAudioTurnRef.current(base64);
      }
    } catch (err) {
      toast.add({ title: "Lỗi lưu âm thanh", description: errorMessage(err), type: "error" });
      setState("idle");
    }
  }, []);

  useEffect(() => {
    stopNativeRecordingRef.current = stopNativeRecording;
  }, [stopNativeRecording]);

  // Native Microphone Recording (MediaRecorder -> Raw Audio)
  const toggleNativeRecording = async () => {
    if (isNativeRecordingRef.current) {
      await stopNativeRecording();
      return;
    }

    try {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      stopSpeaking();

      const recorder = new AudioRecorder();
      nativeRecorderRef.current = recorder;
      await recorder.start();
      isNativeRecordingRef.current = true;
      setState("listening");
      setNativeDuration(0);

      const startTime = Date.now();
      nativeTimerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setNativeDuration(elapsed);
        if (elapsed >= 30) {
          void stopNativeRecordingRef.current();
        }
      }, 500);
    } catch (err) {
      toast.add({ title: "Không thể kích hoạt Micro", description: errorMessage(err), type: "error" });
      setState("idle");
      isNativeRecordingRef.current = false;
    }
  };

  // Web Speech API Recording
  const toggleListening = () => {
    if (state === "listening") {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      return;
    }

    if (typeof window === "undefined") return;
    const win = window as unknown as WindowWithSpeech;
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      toast.add({
        title: "Trình duyệt chưa hỗ trợ Web Speech API",
        description: "Bạn có thể sử dụng ô nhập văn bản bên dưới để đàm thoại.",
        type: "error",
      });
      return;
    }

    try {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      stopSpeaking();

      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setState("listening");
        setTranscript("");
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interim = "";
        let final = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        setTranscript(final || interim);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (event.error !== "no-speech") {
          toast.add({ title: "Lỗi nhận diện âm thanh", description: event.error, type: "error" });
        }
        setState("idle");
      };

      recognition.onend = () => {
        setState("idle");
        if (transcript.trim()) {
          void submitTurn(transcript);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: unknown) {
      toast.add({ title: "Không thể kích hoạt Micro", description: errorMessage(err), type: "error" });
      setState("idle");
    }
  };

  return (
    <div className="flex h-full min-h-[650px] flex-col rounded-2xl border border-slate-200 bg-slate-900/90 text-slate-100 shadow-xl backdrop-blur-md dark:border-slate-800">
      {/* Top Header: Scenario & Accent Bar */}
      <div className="flex flex-col gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Scenario Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {SCENARIOS.map((sc) => {
            const Icon = sc.icon;
            const isSelected = scenario === sc.id;
            return (
              <button
                key={sc.id}
                type="button"
                onClick={() => setScenario(sc.id)}
                className={cn(
                  "cursor-pointer flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-all",
                  isSelected
                    ? "bg-blue-600 text-white shadow-md ring-1 ring-blue-400/50"
                    : "bg-slate-800/80 text-slate-400 hover:bg-slate-800 hover:text-slate-200",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{sc.title}</span>
              </button>
            );
          })}
        </div>

        {/* Mode Selector, Accent Picker & Reset */}
        <div className="flex flex-wrap items-center gap-2 self-end sm:self-center">
          {/* Audio Input Mode Toggle */}
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800/90 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setInputMode("native")}
              className={cn(
                "cursor-pointer rounded-md px-2.5 py-1 font-medium text-[11px] transition",
                inputMode === "native"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200",
              )}
              title="Ghi âm gửi trực tiếp sóng âm thanh lên Gemini Multimodal để phân tích ngữ điệu"
            >
              🎙️ Audio Trực Tiếp
            </button>
            <button
              type="button"
              onClick={() => setInputMode("speech")}
              className={cn(
                "cursor-pointer rounded-md px-2.5 py-1 font-medium text-[11px] transition",
                inputMode === "speech"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200",
              )}
              title="Nhận diện văn bản trên trình duyệt qua Web Speech API"
            >
              ⚡ STT Nhanh
            </button>
          </div>

          <select
            aria-label="Chọn giọng đọc AI"
            value={accent}
            onChange={(e) => setAccent(e.target.value)}
            className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {ACCENTS.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.flag} {acc.label}
              </option>
            ))}
          </select>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => startSession(scenario, accent)}
            className="h-7 cursor-pointer text-xs text-slate-400 hover:text-white"
            title="Bắt đầu lại cuộc hội thoại"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1" /> Làm mới
          </Button>
        </div>
      </div>

      {/* Main Conversation Stream */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
        {messages.map((m) => {
          const isAi = m.role === "ai";
          const isFeedbackOpen = expandedFeedbackId === m.id;

          return (
            <div
              key={m.id}
              className={cn("flex flex-col gap-1.5 max-w-2xl", isAi ? "mr-auto" : "ml-auto items-end")}
            >
              <div className="flex items-center gap-2 text-[11px] text-slate-400 px-1">
                {isAi ? (
                  <>
                    <Bot className="h-3.5 w-3.5 text-blue-400" />
                    <span className="font-semibold text-blue-300">AI Voice Mentor</span>
                  </>
                ) : (
                  <>
                    <span className="font-semibold text-emerald-400">Bạn</span>
                  </>
                )}
                <span>• {m.timestamp}</span>
              </div>

              {/* Message Bubble */}
              <div
                className={cn(
                  "relative rounded-2xl p-4 text-sm leading-relaxed shadow-sm transition-all",
                  isAi
                    ? "bg-slate-800 border border-slate-700/80 text-slate-100 rounded-tl-xs"
                    : "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-xs",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="flex-1">{m.text}</p>
                  {isAi && (m.audioUrl || m.text) && (
                    <button
                      type="button"
                      onClick={() => playAudio(m.audioUrl, m.text)}
                      className="cursor-pointer rounded-full p-1.5 text-slate-400 hover:bg-slate-700 hover:text-blue-300 transition"
                      aria-label="Nghe lại câu này"
                      title="Nghe lại"
                    >
                      <Volume2 className="h-4 w-4" />
                    </button>
                  )}
                </div>

                {/* Score badge for user */}
                {!isAi && m.feedback && (
                  <div className="mt-2.5 flex items-center justify-between border-t border-blue-500/40 pt-2 text-xs">
                    <div className="flex items-center gap-3">
                      <span>
                        Ngữ pháp: <strong className="font-bold">{m.feedback.grammar_score}%</strong>
                      </span>
                      <span>•</span>
                      <span>
                        Lưu loát: <strong className="font-bold">{m.feedback.fluency_score}%</strong>
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => setExpandedFeedbackId(isFeedbackOpen ? null : m.id)}
                      className="cursor-pointer flex items-center gap-1 text-[11px] text-blue-200 hover:text-white transition"
                    >
                      {isFeedbackOpen ? "Thu gọn nhận xét" : "Xem phân tích chi tiết"}
                      {isFeedbackOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                  </div>
                )}
              </div>

              {/* Expandable Real-time Feedback Card */}
              {!isAi && m.feedback && isFeedbackOpen && (
                <Card className="w-full space-y-2.5 rounded-xl border border-blue-500/30 bg-slate-950/80 p-3.5 text-xs shadow-lg animate-in fade-in duration-200">
                  <div className="font-bold text-amber-400 flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5" /> Phân tích huấn luyện viên (Real-time Coaching)
                  </div>

                  {m.feedback.grammar_notes && (
                    <div className="text-slate-300">
                      <span className="font-semibold text-blue-400">📝 Nhận xét ngữ pháp: </span>
                      {m.feedback.grammar_notes}
                    </div>
                  )}

                  {m.feedback.better_expression && (
                    <div className="text-slate-300">
                      <span className="font-semibold text-emerald-400">✨ Diễn đạt tự nhiên hơn: </span>
                      <span className="italic text-slate-200">&ldquo;{m.feedback.better_expression}&rdquo;</span>
                    </div>
                  )}

                  {m.feedback.paraphrase_suggestion && (
                    <div className="text-slate-300">
                      <span className="font-semibold text-purple-400">💡 Paraphrase 800-990+: </span>
                      <code className="text-purple-300 bg-purple-950/60 px-1 py-0.5 rounded font-mono">
                        {m.feedback.paraphrase_suggestion}
                      </code>
                    </div>
                  )}

                  {m.feedback.pronunciation_tips && (
                    <div className="text-slate-300">
                      <span className="font-semibold text-pink-400">🗣️ Mẹo phát âm &amp; âm đuôi: </span>
                      {m.feedback.pronunciation_tips}
                    </div>
                  )}

                  {m.feedback.acoustic_notes && (
                    <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-300 border border-emerald-500/20">
                      <span className="font-semibold text-emerald-400">🌊 Phân tích sóng âm &amp; Ngữ điệu: </span>
                      {m.feedback.acoustic_notes}
                    </div>
                  )}
                </Card>
              )}
            </div>
          );
        })}

        {/* Live speech transcription / native recording preview */}
        {state === "listening" && (
          <div className="flex flex-col gap-1.5 max-w-2xl ml-auto items-end animate-pulse">
            <div className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
              {inputMode === "native"
                ? `Đang thu âm sóng âm trực tiếp... (${nativeDuration}s / 30s)`
                : "Đang lắng nghe bạn nói..."}
            </div>
            <div className="rounded-2xl bg-slate-800/80 border border-emerald-500/40 p-4 text-sm text-emerald-200 italic">
              {inputMode === "native"
                ? "Nói câu tiếng Anh của bạn vào micro, sau đó bấm lại nút Micro để gửi trực tiếp cho Gemini."
                : (transcript || "Hãy nói câu trả lời của bạn bằng tiếng Anh...")}
            </div>
          </div>
        )}

        {/* Thinking Indicator */}
        {state === "thinking" && (
          <div className="flex items-center gap-2 text-xs text-slate-400 mr-auto p-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
            <span>AI đang lắng nghe và chấm điểm phát âm...</span>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Bottom Controls & Mic Visualizer */}
      <div className="border-t border-slate-800 bg-slate-950/60 p-4 space-y-3">
        {/* Animated Audio Orb / Status */}
        <div className="flex items-center justify-center gap-4">
          {/* Large Mic Button */}
          <button
            type="button"
            onClick={inputMode === "native" ? toggleNativeRecording : toggleListening}
            className={cn(
              "relative flex h-16 w-16 cursor-pointer items-center justify-center rounded-full transition-all duration-300 shadow-xl",
              state === "listening"
                ? "bg-red-500 text-white ring-8 ring-red-500/20 animate-pulse scale-105"
                : state === "speaking"
                ? "bg-blue-600 text-white ring-8 ring-blue-500/20"
                : "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white hover:scale-105 hover:shadow-blue-500/25",
            )}
            title={state === "listening" ? "Nhấn để dừng và gửi" : "Bấm để nói tiếng Anh"}
            aria-label="Microphone"
          >
            {state === "listening" ? (
              inputMode === "native" ? <Square className="h-6 w-6" /> : <MicOff className="h-7 w-7" />
            ) : state === "thinking" ? (
              <Loader2 className="h-7 w-7 animate-spin" />
            ) : (
              <Mic className="h-7 w-7" />
            )}
          </button>
        </div>

        <div className="text-center text-xs text-slate-400">
          {state === "listening" ? (
            <span className="text-emerald-400 font-semibold">
              {inputMode === "native"
                ? `Đang ghi âm sóng âm (${nativeDuration}s)... Bấm nút vuông để gửi phân tích`
                : "Đang thu âm... Nói xong hãy bấm lại nút Mic để gửi"}
            </span>
          ) : state === "speaking" ? (
            <span className="text-blue-400 font-semibold">AI đang đọc phản hồi...</span>
          ) : state === "thinking" ? (
            <span className="text-purple-400">Đang phân tích phản xạ &amp; ngữ điệu âm thanh...</span>
          ) : (
            <span>
              {inputMode === "native"
                ? "🎙️ Chế độ Audio trực tiếp: Bấm nút Micro để ghi âm giọng nói gửi lên AI"
                : "⚡ Chế độ STT Nhanh: Bấm nút Micro để nói tiếng Anh (hoặc gõ bên dưới)"}
            </span>
          )}
        </div>

        {/* Fallback Text Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submitTurn(manualText);
          }}
          className="flex items-center gap-2 max-w-xl mx-auto"
        >
          <Input
            aria-label="Nhập câu tiếng Anh"
            placeholder="Hoặc gõ câu đối thoại bằng tiếng Anh..."
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            disabled={state === "thinking"}
            className="border-slate-700 bg-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!manualText.trim() || state === "thinking"}
            className="cursor-pointer bg-blue-600 hover:bg-blue-500 text-xs shrink-0"
          >
            <Send className="h-3.5 w-3.5 mr-1" /> Gửi
          </Button>
        </form>
      </div>
    </div>
  );
}
