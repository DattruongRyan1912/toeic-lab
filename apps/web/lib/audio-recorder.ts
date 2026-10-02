"use client";

export function getSupportedAudioMime(): string {
  if (typeof window === "undefined" || typeof MediaRecorder === "undefined") {
    return "audio/webm";
  }
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
    "audio/wav",
  ];
  for (const mime of candidates) {
    if (MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return "";
}

export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("Failed to convert audio blob to base64"));
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export interface AudioRecorderOptions {
  autoStopOnSilence?: boolean;
  silenceThreshold?: number; // 0 to 1, default 0.04
  speechThreshold?: number; // 0 to 1, default 0.07
  silenceDurationMs?: number; // default 1000ms
  onSilence?: () => void;
  onVolumeChange?: (volume: number) => void;
  onSpeechDetected?: () => void;
}

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animFrameId: number | null = null;
  private options: AudioRecorderOptions;
  private hasSpoken = false;
  private silenceStart: number | null = null;
  private isStopped = false;

  constructor(options: AudioRecorderOptions = {}) {
    this.options = {
      autoStopOnSilence: false,
      silenceThreshold: 0.04,
      speechThreshold: 0.07,
      silenceDurationMs: 1000,
      ...options,
    };
  }

  async start(): Promise<void> {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("Trình duyệt không hỗ trợ thu âm Microphone (MediaDevices API)");
    }

    // Initialize AudioContext immediately on user gesture to prevent 'suspended' state on iOS/Android
    if (typeof window !== "undefined") {
      try {
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (AudioCtx) {
          this.audioContext = new AudioCtx();
          if (this.audioContext.state === "suspended") {
            await this.audioContext.resume();
          }
        }
      } catch (e) {
        console.warn("Could not pre-init AudioContext:", e);
      }
    }

    this.chunks = [];
    this.hasSpoken = false;
    this.silenceStart = null;
    this.isStopped = false;

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    if (this.audioContext && this.audioContext.state === "suspended") {
      try {
        await this.audioContext.resume();
      } catch {
        // ignore
      }
    }

    const mimeType = getSupportedAudioMime();
    const options: MediaRecorderOptions = mimeType ? { mimeType } : {};

    this.mediaRecorder = new MediaRecorder(this.stream, options);

    this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) {
        this.chunks.push(event.data);
      }
    };

    this.mediaRecorder.start(100); // 100ms timeslice for steady chunk streaming
    this.startVolumeMonitoring();
  }

  private startVolumeMonitoring(): void {
    if (!this.stream || typeof window === "undefined") return;

    try {
      if (!this.audioContext) {
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (!AudioCtx) return;
        this.audioContext = new AudioCtx();
      }

      if (this.audioContext.state === "suspended") {
        void this.audioContext.resume();
      }

      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.4;
      source.connect(this.analyser);

      const bufferLength = this.analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const checkVolume = () => {
        if (!this.analyser || this.isStopped) return;

        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        // Boost sensitivity for mobile built-in microphones
        const normalized = Math.min(1, (avg / 96) * 1.2); // 0 to 1

        this.options.onVolumeChange?.(normalized);

        // Speech & Silence detection
        if (this.options.autoStopOnSilence) {
          const speechThresh = this.options.speechThreshold ?? 0.07;
          const silenceThresh = this.options.silenceThreshold ?? 0.04;
          const silenceMs = this.options.silenceDurationMs ?? 1000;

          if (normalized >= speechThresh) {
            if (!this.hasSpoken) {
              this.hasSpoken = true;
              this.options.onSpeechDetected?.();
            }
            this.silenceStart = null;
          } else if (this.hasSpoken && normalized < silenceThresh) {
            if (this.silenceStart === null) {
              this.silenceStart = Date.now();
            } else if (Date.now() - this.silenceStart >= silenceMs) {
              // User spoke and then was silent for silenceMs
              this.options.onSilence?.();
              return;
            }
          }
        }

        this.animFrameId = requestAnimationFrame(checkVolume);
      };

      this.animFrameId = requestAnimationFrame(checkVolume);
    } catch (e) {
      console.warn("Volume monitoring initialization failed:", e);
    }
  }

  isRecording(): boolean {
    return this.mediaRecorder !== null && this.mediaRecorder.state === "recording";
  }

  async stop(): Promise<{ blob: Blob; base64: string }> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        this.cleanup();
        reject(new Error("Micro chưa được khởi động"));
        return;
      }

      const recorder = this.mediaRecorder;
      const chunks = this.chunks;
      const mimeType = recorder.mimeType || "audio/webm";

      recorder.onstop = async () => {
        try {
          const blob = new Blob(chunks, { type: mimeType });
          const base64 = await blobToBase64(blob);
          this.cleanup();
          resolve({ blob, base64 });
        } catch (err) {
          this.cleanup();
          reject(err);
        }
      };

      try {
        if (recorder.state === "recording") {
          recorder.stop();
        } else {
          const blob = new Blob(chunks, { type: mimeType });
          blobToBase64(blob)
            .then((base64) => {
              this.cleanup();
              resolve({ blob, base64 });
            })
            .catch((err) => {
              this.cleanup();
              reject(err);
            });
        }
      } catch (err) {
        this.cleanup();
        reject(err);
      }
    });
  }

  cancel(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      try {
        this.mediaRecorder.stop();
      } catch {
        // ignore
      }
    }
    this.cleanup();
  }

  private cleanup(): void {
    this.isStopped = true;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      void this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    this.analyser = null;

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.chunks = [];
  }
}
