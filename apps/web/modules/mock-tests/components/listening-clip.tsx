"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Pause, Play, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { speak } from "@/lib/audio";
import type { PracticeQuestion } from "@/types";

interface ListeningClipProps {
  question: PracticeQuestion;
  /** Exam conditions: the clip plays once, like the real test. */
  playOnce: boolean;
  played: boolean;
  onPlayed: () => void;
}

function ttsScript(q: PracticeQuestion): string {
  const choices = [q.choice_a, q.choice_b, q.choice_c, q.choice_d]
    .map((text, i) => (text ? `${"ABCD"[i]}. ${text}` : null))
    .filter(Boolean)
    .join(" ... ");
  return q.part === "Part 1" ? `Question ${q.question_no}. ${choices}` : `${q.sentence} ... ${choices}`;
}

/** Authentic ETS audio for Part 1-4 (TTS only when a question has no recording yet). */
export function ListeningClip({ question, playOnce, played, onPlayed }: ListeningClipProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const authentic = Boolean(question.audio_url);
  const locked = playOnce && played && !playing;

  useEffect(() => {
    const audio = audioRef.current;
    return () => audio?.pause(); // leaving the question stops its clip
  }, [question.id]);

  const toggle = async () => {
    if (locked) return;
    if (!authentic) {
      onPlayed();
      setPlaying(true);
      try {
        await speak(ttsScript(question));
      } finally {
        setPlaying(false);
      }
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      if (playOnce) return; // exam: no pausing to re-listen
      audio.pause();
      return;
    }
    onPlayed();
    await audio.play().catch(() => setPlaying(false));
  };

  return (
    <div className="flex items-center gap-2">
      {authentic && (
        <audio
          ref={audioRef}
          src={question.audio_url ?? undefined}
          preload="none"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
        />
      )}
      <Button variant="outline" size="sm" disabled={locked} onClick={() => void toggle()} className="shrink-0 cursor-pointer text-xs">
        {playing ? (
          playOnce ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Pause className="h-3.5 w-3.5" aria-hidden="true" />
        ) : authentic ? (
          <Play className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {locked ? "Đã nghe (thi thật chỉ phát 1 lần)" : playing ? "Đang phát" : played ? "Nghe lại" : "Nghe"}
      </Button>
      <span className="text-[10px] text-slate-500 dark:text-slate-400">{authentic ? "Audio gốc ETS" : "Giọng đọc máy (chưa có audio gốc)"}</span>
    </div>
  );
}
