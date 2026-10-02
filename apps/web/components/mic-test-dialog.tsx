"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Mic,
  Sliders,
  Square,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface MicTestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type PermissionStatusType = "granted" | "denied" | "prompt" | "unsupported";

export function MicTestDialog({ open, onOpenChange }: MicTestDialogProps) {
  const [testing, setTesting] = useState(false);
  const [volume, setVolume] = useState(0);
  const [maxVolume, setMaxVolume] = useState(0);
  const [permissionStatus, setPermissionStatus] = useState<PermissionStatusType>("prompt");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recognizedText, setRecognizedText] = useState<string>("");
  const [speechApiSupported] = useState(() => {
    if (typeof window === "undefined") return false;
    const win = window as unknown as {
      SpeechRecognition?: unknown;
      webkitSpeechRecognition?: unknown;
    };
    return Boolean(win.SpeechRecognition || win.webkitSpeechRecognition);
  });
  const [activeGuideTab, setActiveGuideTab] = useState<"ios" | "android" | "desktop">(() => {
    if (typeof navigator === "undefined") return "ios";
    const ua = navigator.userAgent.toLowerCase();
    if (/iphone|ipad|ipod/.test(ua)) return "ios";
    if (/android/.test(ua)) return "android";
    return "desktop";
  });

  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const recognitionRef = useRef<{ stop: () => void; abort: () => void } | null>(null);

  // Check initial permissions from browser
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (navigator.permissions?.query) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      navigator.permissions.query({ name: "microphone" as any })
        .then((res) => {
          setPermissionStatus(res.state as PermissionStatusType);
          res.onchange = () => {
            setPermissionStatus(res.state as PermissionStatusType);
          };
        })
        .catch(() => {
          setPermissionStatus("prompt");
        });
    }
  }, []);

  const cleanup = useCallback(() => {
    if (animFrameRef.current !== null) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      void audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setTesting(false);
    setVolume(0);
  }, []);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      cleanup();
      setErrorMessage(null);
      setRecognizedText("");
      setMaxVolume(0);
    }
    onOpenChange(nextOpen);
  };

  const startTest = async () => {
    cleanup();
    setErrorMessage(null);
    setRecognizedText("");
    setMaxVolume(0);

    try {
      if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
        throw new Error("Trình duyệt không hỗ trợ MediaDevices (Microphone API).");
      }

      // 1. AudioContext setup in direct user gesture
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        audioContextRef.current = new AudioCtx();
        if (audioContextRef.current.state === "suspended") {
          await audioContextRef.current.resume();
        }
      }

      // 2. Request mic permission and stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      setPermissionStatus("granted");

      // 3. Connect analyser
      if (audioContextRef.current) {
        if (audioContextRef.current.state === "suspended") {
          await audioContextRef.current.resume();
        }
        const source = audioContextRef.current.createMediaStreamSource(stream);
        const analyser = audioContextRef.current.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.4;
        source.connect(analyser);
        analyserRef.current = analyser;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const updateMeter = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          const avg = sum / bufferLength;
          // Boosted normalized volume (0 - 100%)
          const norm = Math.min(100, Math.round((avg / 96) * 120));
          setVolume(norm);
          setMaxVolume((prev) => Math.max(prev, norm));
          animFrameRef.current = requestAnimationFrame(updateMeter);
        };
        animFrameRef.current = requestAnimationFrame(updateMeter);
      }

      // 4. Test Web Speech API if supported
      const win = window as unknown as {
        SpeechRecognition?: new () => {
          lang: string;
          continuous: boolean;
          interimResults: boolean;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onresult: (e: any) => void;
          onerror: (e: unknown) => void;
          start: () => void;
          stop: () => void;
          abort: () => void;
        };
        webkitSpeechRecognition?: new () => {
          lang: string;
          continuous: boolean;
          interimResults: boolean;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onresult: (e: any) => void;
          onerror: (e: unknown) => void;
          start: () => void;
          stop: () => void;
          abort: () => void;
        };
      };
      const SpeechRec = win.SpeechRecognition || win.webkitSpeechRecognition;
      if (SpeechRec) {
        try {
          const rec = new SpeechRec();
          rec.lang = "en-US";
          rec.continuous = true;
          rec.interimResults = true;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          rec.onresult = (e: any) => {
            let full = "";
            for (let i = 0; i < e.results.length; i++) {
              const text = e.results[i]?.[0]?.transcript;
              if (text) full += (full ? " " : "") + text.trim();
            }
            if (full) setRecognizedText(full);
          };
          rec.onerror = (e) => {
            console.warn("SpeechRec test error:", e);
          };
          rec.start();
          recognitionRef.current = rec;
        } catch {
          // ignore
        }
      }

      setTesting(true);
    } catch (err: unknown) {
      cleanup();
      const errorObj = err as { name?: string; message?: string };
      if (errorObj.name === "NotAllowedError" || errorObj.name === "PermissionDeniedError") {
        setPermissionStatus("denied");
        setErrorMessage("Quyền truy cập Microphone bị từ chối trên thiết bị của bạn. Vui lòng cấp quyền theo hướng dẫn bên dưới.");
      } else {
        setErrorMessage(errorObj.message || "Không thể khởi động Microphone.");
      }
    }
  };

  const getVolumeLevelText = (vol: number) => {
    if (vol < 5) return "Im lặng (Không có tiếng nói)";
    if (vol < 20) return "Âm lượng nhỏ (Hãy nói to hơn một chút)";
    if (vol < 65) return "Âm lượng tiêu chuẩn (Rất tốt! 🎉)";
    return "Âm lượng to (Rất rõ ràng)";
  };

  const getVolumeLevelColor = (vol: number) => {
    if (vol < 5) return "text-slate-400";
    if (vol < 20) return "text-amber-500";
    if (vol < 65) return "text-emerald-500";
    return "text-blue-500";
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md p-5 sm:p-6 overflow-hidden max-h-[90vh] flex flex-col z-[60]">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
            <Sliders className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Kiểm tra & Chuẩn đoán Microphone
          </DialogTitle>
        </DialogHeader>

        <div className="overflow-y-auto space-y-4 pr-1 text-xs">
          {/* Status summary banner */}
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-2.5 dark:border-slate-800 dark:bg-slate-900/60">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Quyền Microphone</span>
              <div className="mt-1 flex items-center justify-center gap-1 font-bold">
                {permissionStatus === "granted" ? (
                  <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Đã cho phép
                  </span>
                ) : permissionStatus === "denied" ? (
                  <span className="text-red-600 dark:text-red-400 flex items-center gap-1">
                    <XCircle className="h-3.5 w-3.5" /> Bị từ chối
                  </span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <AlertCircle className="h-3.5 w-3.5" /> Cần cấp quyền
                  </span>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-2.5 dark:border-slate-800 dark:bg-slate-900/60">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Nhận diện giọng nói STT</span>
              <div className="mt-1 flex items-center justify-center gap-1 font-bold">
                {speechApiSupported ? (
                  <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Trình duyệt hỗ trợ
                  </span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1" title="Sử dụng phân tích Audio trực tiếp hoặc DeepSeek STT">
                    <AlertTriangle className="h-3.5 w-3.5" /> Cần Chrome/Safari mới
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Test area */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/40 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                Thử nghiệm cường độ âm thanh
              </span>
              {testing && (
                <span className="flex items-center gap-1 text-[11px] font-mono font-bold text-red-500 animate-pulse">
                  <span className="h-2 w-2 rounded-full bg-red-500" /> Đang thu âm
                </span>
              )}
            </div>

            {/* Visualizer & volume meter */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className={cn("font-medium", getVolumeLevelColor(volume))}>
                  {testing ? getVolumeLevelText(volume) : "Nhấn nút bên dưới để thử nói"}
                </span>
                <span className="font-mono font-bold text-slate-600 dark:text-slate-300">
                  {volume}% {maxVolume > 0 && `(Max: ${maxVolume}%)`}
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-3 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-75",
                    volume < 15
                      ? "bg-slate-400"
                      : volume < 65
                        ? "bg-emerald-500"
                        : "bg-blue-500",
                  )}
                  style={{ width: `${Math.min(100, Math.max(0, volume))}%` }}
                />
              </div>

              {/* Realtime bouncing wave */}
              {testing && (
                <div className="flex items-center justify-center gap-1.5 h-7 pt-1">
                  {[0.3, 0.6, 0.9, 1.2, 0.9, 0.6, 0.3].map((f, i) => (
                    <span
                      key={i}
                      className={cn(
                        "w-1.5 rounded-full transition-all duration-75",
                        volume > 10 ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700",
                      )}
                      style={{
                        height: `${Math.max(4, (volume * f * 24) / 100)}px`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Recognized text preview */}
            {testing && (
              <div className="rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-800 dark:bg-slate-900/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                  Văn bản nhận diện trực tiếp (Hãy nói thử: &ldquo;hello&rdquo;, &ldquo;contract&rdquo;):
                </span>
                <p className="mt-1 font-mono text-xs font-bold text-blue-600 dark:text-blue-400 min-h-[18px]">
                  {recognizedText ? `"${recognizedText}"` : "… đang lắng nghe giọng nói"}
                </p>
              </div>
            )}

            {/* Error banner */}
            {errorMessage && (
              <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-2.5 text-xs text-red-600 dark:text-red-400">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold">Lỗi khởi động Micro</p>
                  <p className="mt-0.5 text-[11px] leading-relaxed">{errorMessage}</p>
                </div>
              </div>
            )}

            {/* Test Action Buttons */}
            <div className="flex items-center justify-center gap-3 pt-1">
              {!testing ? (
                <Button
                  onClick={() => void startTest()}
                  className="cursor-pointer gap-2 bg-blue-600 hover:bg-blue-500 text-white shadow-xs"
                >
                  <Mic className="h-4 w-4" /> Bắt đầu thử Micro
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  onClick={cleanup}
                  className="cursor-pointer gap-2 shadow-xs"
                >
                  <Square className="h-4 w-4" /> Dừng thử nghiệm
                </Button>
              )}
            </div>
          </div>

          {/* Guide Section for Mobile / Desktop */}
          <div className="space-y-2">
            <div className="flex items-center justify-between border-b border-slate-200 pb-1.5 dark:border-slate-800">
              <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <HelpCircle className="h-4 w-4 text-amber-500" />
                Hướng dẫn cấp quyền Microphone
              </span>
              <div className="flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setActiveGuideTab("ios")}
                  className={cn(
                    "cursor-pointer rounded-md px-2 py-0.5 text-[10px] font-semibold transition",
                    activeGuideTab === "ios"
                      ? "bg-blue-600 text-white"
                      : "text-slate-600 dark:text-slate-400",
                  )}
                >
                  iPhone / Safari
                </button>
                <button
                  type="button"
                  onClick={() => setActiveGuideTab("android")}
                  className={cn(
                    "cursor-pointer rounded-md px-2 py-0.5 text-[10px] font-semibold transition",
                    activeGuideTab === "android"
                      ? "bg-blue-600 text-white"
                      : "text-slate-600 dark:text-slate-400",
                  )}
                >
                  Android
                </button>
                <button
                  type="button"
                  onClick={() => setActiveGuideTab("desktop")}
                  className={cn(
                    "cursor-pointer rounded-md px-2 py-0.5 text-[10px] font-semibold transition",
                    activeGuideTab === "desktop"
                      ? "bg-blue-600 text-white"
                      : "text-slate-600 dark:text-slate-400",
                  )}
                >
                  Máy tính
                </button>
              </div>
            </div>

            {/* iOS Guide */}
            {activeGuideTab === "ios" && (
              <div className="space-y-2 rounded-xl border border-blue-200/60 bg-blue-50/40 p-3 text-[11px] leading-relaxed text-slate-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-slate-300">
                <p className="font-semibold text-blue-700 dark:text-blue-300">
                  Cách 1: Cho phép trực tiếp trên Safari
                </p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Bấm vào biểu tượng <strong>&ldquo;aA&rdquo;</strong> (hoặc icon Cài đặt) ở bên trái thanh nhập địa chỉ web.</li>
                  <li>Chọn <strong>Cài đặt trang web (Website Settings)</strong>.</li>
                  <li>Tại mục <strong>Micrô (Microphone)</strong>, chuyển sang <strong>Cho phép (Allow)</strong>.</li>
                  <li>Tải lại trang (F5/Reload) để áp dụng.</li>
                </ol>
                <p className="font-semibold text-blue-700 dark:text-blue-300 pt-1">
                  Cách 2: Nếu Safari bị khóa quyền hệ thống
                </p>
                <p>
                  Vào <strong>Cài đặt của iPhone</strong> ➔ Cuộn xuống chọn <strong>Safari</strong> ➔ Kéo xuống mục <strong>Micrô (Microphone)</strong> ➔ Chọn <strong>Cho phép</strong>.
                </p>
              </div>
            )}

            {/* Android Guide */}
            {activeGuideTab === "android" && (
              <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-300">
                <p className="font-semibold text-slate-900 dark:text-white">
                  Dành cho Chrome / Cốc Cốc / Edge trên Android:
                </p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Chạm vào biểu tượng <strong>Ổ khóa (hoặc Tuỳ chọn cài đặt)</strong> bên trái thanh địa chỉ web.</li>
                  <li>Chọn <strong>Quyền (Permissions)</strong> ➔ Bật công tắc <strong>Microphone</strong> sang Cho phép.</li>
                  <li>Nếu trang web chưa hỏi, bấm nút <strong>&ldquo;Bắt đầu thử Micro&rdquo;</strong> ở trên rồi chọn <strong>&ldquo;Cho phép khi dùng ứng dụng&rdquo;</strong>.</li>
                </ol>
              </div>
            )}

            {/* Desktop Guide */}
            {activeGuideTab === "desktop" && (
              <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-300">
                <p className="font-semibold text-slate-900 dark:text-white">
                  Dành cho Chrome, Edge, Safari trên macOS / Windows:
                </p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Bấm vào biểu tượng <strong>Cài đặt trang web (Tune/Lock icon)</strong> bên trái URL.</li>
                  <li>Bật quyền <strong>Microphone: Allow</strong>.</li>
                  <li>Trên macOS: Kiểm tra <em>System Settings &gt; Privacy &amp; Security &gt; Microphone</em> đã tick cho trình duyệt chưa.</li>
                </ol>
              </div>
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleOpenChange(false)}
            className="cursor-pointer text-xs"
          >
            Đóng
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
