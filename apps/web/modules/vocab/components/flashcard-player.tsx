"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";
import { ArrowRight, BookOpen, CheckCircle, Languages, Loader2, Mic, RotateCcw, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { speak } from "@/lib/audio";
import { ipa } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { FlashcardItem, SrsCard } from "@/types";
import { PronounceDialog } from "./pronounce-dialog";

const RATINGS = [
  { value: 1, label: "Again", shortHint: "Quên", hint: "Quên — ôn lại ngày mai", style: "bg-red-50 hover:bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:hover:bg-red-500/20 dark:text-red-400 dark:border-red-500/30" },
  { value: 2, label: "Hard", shortHint: "Khó", hint: "Nhớ nhưng khó", style: "bg-amber-50 hover:bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:hover:bg-amber-500/20 dark:text-amber-400 dark:border-amber-500/30" },
  { value: 3, label: "Good", shortHint: "Nhớ", hint: "Nhớ tốt", style: "bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:hover:bg-blue-500/20 dark:text-blue-400 dark:border-blue-500/30" },
  { value: 4, label: "Easy", shortHint: "Rất dễ", hint: "Rất dễ — giãn cách dài", style: "bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:hover:bg-emerald-500/20 dark:text-emerald-400 dark:border-emerald-500/30" },
];

const STATE_LABEL: Record<SrsCard["state"], string> = { new: "Thẻ mới", learning: "Đang học", review: "Ôn tập", mastered: "Đã thuộc" };

interface FlashcardPlayerProps {
  queue: SrsCard[];
  onReviewed: () => void;
  onReload: () => void;
  selectedCategory?: string;
  studyMode?: "srs" | "all" | "new";
  onSelectCategory?: (category: string) => void;
  onSwitchMode?: (mode: "srs" | "all" | "new") => void;
  totalCardsInCategory?: number;
}

export function FlashcardPlayer({
  queue,
  onReviewed,
  onReload,
  selectedCategory,
  studyMode = "srs",
  onSelectCategory,
  onSwitchMode,
  totalCardsInCategory,
}: FlashcardPlayerProps) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [saving, setSaving] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [reviewed, setReviewed] = useState(0);
  const [pronouncingWord, setPronouncingWord] = useState<FlashcardItem | null>(null);
  const [translations, setTranslations] = useState<Record<number, string>>({});
  const [translatingId, setTranslatingId] = useState<number | null>(null);

  const card = queue[index];
  const finished = queue.length > 0 && index >= queue.length;
  const shownAt = useRef(0);

  // Time on card = from showing it to rating it (server caps outliers, e.g. a break mid-session).
  useEffect(() => {
    shownAt.current = Date.now();
  }, [index]);

  const play = useCallback(async (text: string) => {
    setPlaying(true);
    try {
      await speak(text);
    } finally {
      setPlaying(false);
    }
  }, []);

  const handleTranslateExample = useCallback(async (cardId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (translatingId) return;
    setTranslatingId(cardId);
    try {
      const updated = await api<FlashcardItem>(`/flashcards/${cardId}/translate-example`, { method: "POST" });
      if (updated.example_translation) {
        setTranslations((prev) => ({ ...prev, [cardId]: updated.example_translation! }));
      }
    } catch (err) {
      toast.add({ title: "Không thể dịch câu ví dụ", description: errorMessage(err), type: "error" });
    } finally {
      setTranslatingId(null);
    }
  }, [translatingId]);

  const rate = useCallback(
    async (rating: number) => {
      if (!card || saving) return;
      setSaving(true);
      try {
        const durationMs = shownAt.current ? Math.min(Date.now() - shownAt.current, 600_000) : null;
        await api(`/flashcards/${card.card_id}/review`, { method: "POST", json: { rating, duration_ms: durationMs } });
        setReviewed((n) => n + 1);
        setFlipped(false);
        setIndex((i) => i + 1);
        onReviewed();
        if (index + 1 >= queue.length) confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
      } catch (error) {
        toast.add({ title: "Chưa lưu được kết quả ôn", description: errorMessage(error), type: "error" });
      } finally {
        setSaving(false);
      }
    },
    [card, index, queue.length, onReviewed, saving],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (!card || target?.closest("input, textarea, [contenteditable=true]")) return;
      if (event.code === "Space") {
        event.preventDefault();
        setFlipped((f) => !f);
      } else if (flipped && ["1", "2", "3", "4"].includes(event.key)) {
        void rate(Number(event.key));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [card, flipped, rate]);

  if (queue.length === 0) {
    const isFiltered = Boolean(selectedCategory && selectedCategory !== "all");
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center dark:border-slate-700/70 dark:bg-slate-800/60">
        <BookOpen className="mx-auto mb-4 h-12 w-12 text-slate-400" aria-hidden="true" />
        <h3 className="mb-2 text-xl font-bold text-slate-900 dark:text-slate-100">
          {isFiltered
            ? `Chưa có thẻ đến hạn cho chủ đề "${selectedCategory}" 🎉`
            : "Không còn thẻ cần học hôm nay 🎉"}
        </h3>
        <p className="mx-auto max-w-md text-sm text-slate-500 dark:text-slate-400">
          {isFiltered
            ? `Các thẻ trong chủ đề này đang trong khoảng giãn cách SM-2. Bạn có thể luyện tập tăng cường toàn bộ từ trong chủ đề hoặc chuyển sang chủ đề khác.`
            : "Các thẻ đã ôn đang trong khoảng giãn cách SM-2 và hạn mức thẻ mới hôm nay đã dùng hết. Quay lại vào ngày mai hoặc thêm từ mới."}
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {isFiltered && onSwitchMode && studyMode !== "all" && (
            <Button onClick={() => onSwitchMode("all")} variant="default" className="cursor-pointer">
              <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
              Luyện tăng cường toàn bộ chủ đề {totalCardsInCategory ? `(${totalCardsInCategory} từ)` : ""}
            </Button>
          )}
          {isFiltered && onSelectCategory && (
            <Button onClick={() => onSelectCategory("all")} variant="outline" className="cursor-pointer">
              Học tất cả chủ đề khác
            </Button>
          )}
          <Button onClick={onReload} variant="outline" className="cursor-pointer">
            <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" /> Làm mới dữ liệu
          </Button>
        </div>
      </div>
    );
  }

  if (finished || !card) {
    return (
      <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-12 text-center dark:border-slate-700/70 dark:bg-slate-800/60">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-emerald-300 bg-emerald-50 text-emerald-600 dark:border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-400">
          <CheckCircle className="h-8 w-8" aria-hidden="true" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 dark:text-white">Hoàn thành phiên ôn!</h3>
        <p className="mx-auto max-w-md text-sm text-slate-500 dark:text-slate-400">
          Đã ôn {reviewed} thẻ{selectedCategory && selectedCategory !== "all" ? ` thuộc chủ đề "${selectedCategory}"` : ""}. Lịch ôn tiếp theo của từng thẻ đã được SM-2 tính lại và cập nhật vào Dashboard.
        </p>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <Button onClick={onReload} variant="outline" className="cursor-pointer">
            <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" /> Kiểm tra thẻ đến hạn
          </Button>
          {selectedCategory && selectedCategory !== "all" && onSwitchMode && studyMode !== "all" && (
            <Button onClick={() => onSwitchMode("all")} variant="default" className="cursor-pointer">
              Luyện tăng cường lại chủ đề này
            </Button>
          )}
          {onSelectCategory && (
            <Button onClick={() => onSelectCategory("all")} variant="ghost" className="cursor-pointer">
              Đổi chủ đề khác
            </Button>
          )}
        </div>
      </div>
    );
  }

  const word = card.flashcard;
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="flex items-center justify-between px-2 text-sm text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
          Thẻ {index + 1} / {queue.length}
        </span>
        <span className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">{STATE_LABEL[card.state]}</span>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">{word.category}</span>
        </span>
      </div>

      <div
        role="button"
        tabIndex={0}
        aria-label={flipped ? "Lật về mặt trước" : "Lật thẻ xem nghĩa"}
        onClick={() => setFlipped((f) => !f)}
        onKeyDown={(event) => event.key === "Enter" && setFlipped((f) => !f)}
        className="h-[430px] sm:h-[400px] w-full cursor-pointer rounded-2xl select-none [perspective:1000px]"
      >
        <div className={cn("relative h-full w-full rounded-2xl shadow-xl transition-transform duration-500 [transform-style:preserve-3d]", flipped && "[transform:rotateY(180deg)]")}>
          <div className="absolute inset-0 flex h-full w-full flex-col justify-between rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-5 sm:p-8 [backface-visibility:hidden] dark:border-slate-700 dark:from-slate-800 dark:to-slate-900">
            <div className="flex items-start justify-between">
              <span className="rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold tracking-wider text-blue-700 uppercase dark:border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400">
                {word.word_type || "Vocabulary"}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    void play(word.word);
                  }}
                  disabled={playing}
                  className="cursor-pointer rounded-full border border-slate-200 bg-slate-100 p-2.5 text-slate-600 transition hover:text-blue-600 dark:border-slate-700/50 dark:bg-slate-800/60 dark:text-slate-300 dark:hover:text-blue-400"
                  aria-label={`Nghe phát âm ${word.word}`}
                  title="Nghe phát âm mẫu"
                >
                  <Volume2 className={cn("h-5 w-5", playing && "animate-bounce text-blue-500")} />
                </button>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    setPronouncingWord(word);
                  }}
                  className="cursor-pointer rounded-full border border-blue-200 bg-blue-50 p-2.5 text-blue-600 transition hover:bg-blue-100 hover:text-blue-700 dark:border-blue-500/30 dark:bg-blue-600/20 dark:text-blue-400 dark:hover:bg-blue-600/30"
                  aria-label={`Luyện phát âm ${word.word} với AI`}
                  title="Luyện phát âm với AI"
                >
                  <Mic className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="my-auto space-y-3 text-center">
              <h2 className="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl md:text-5xl dark:text-white">{word.word}</h2>
              {word.ipa && <p className="font-mono text-base sm:text-lg text-slate-500 dark:text-slate-400">{ipa(word.ipa)}</p>}
            </div>
            <div className="flex items-center justify-center gap-1 text-center text-xs text-slate-500">
              <span>Chạm hoặc nhấn Space để xem nghĩa</span>
              <ArrowRight className="h-3 w-3" aria-hidden="true" />
            </div>
          </div>

          <div className="absolute inset-0 flex h-full w-full flex-col justify-between overflow-y-auto rounded-2xl border border-blue-300 bg-gradient-to-b from-white to-slate-50 p-4 sm:p-6 [transform:rotateY(180deg)] [backface-visibility:hidden] dark:border-blue-500/40 dark:from-slate-800 dark:to-slate-900">
            <div className="space-y-3">
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase">Nghĩa tiếng Việt</span>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{word.meaning}</p>
              </div>
              {word.collocations && (
                <div className="rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-700/80 dark:bg-slate-900/60">
                  <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">Collocations:</span>
                  <p className="mt-0.5 text-sm font-medium text-slate-700 dark:text-slate-300">{word.collocations}</p>
                </div>
              )}
              {word.paraphrase_pair && (
                <div className="rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-700/80 dark:bg-slate-900/60">
                  <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">Paraphrase Vault:</span>
                  <p className="mt-0.5 text-sm font-medium text-slate-700 dark:text-slate-300">{word.paraphrase_pair}</p>
                </div>
              )}
              {word.example_sentence && (() => {
                const exampleTrans = translations[word.id] || word.example_translation;
                return (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                      <span className="flex items-center gap-1.5">
                        Ví dụ chuẩn đề thi
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            void play(word.example_sentence);
                          }}
                          className="cursor-pointer text-blue-600 hover:text-blue-700 dark:text-blue-400"
                          aria-label="Nghe câu ví dụ"
                          title="Nghe phát âm cả câu"
                        >
                          <Volume2 className="h-3.5 w-3.5" />
                        </button>
                      </span>
                      {!exampleTrans && (
                        <button
                          type="button"
                          onClick={(e) => void handleTranslateExample(word.id, e)}
                          disabled={translatingId === word.id}
                          className="flex cursor-pointer items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
                          title="Dịch nghĩa câu ví dụ với AI"
                        >
                          {translatingId === word.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Languages className="h-3 w-3" />
                          )}
                          Dịch nghĩa
                        </button>
                      )}
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-800 dark:bg-slate-900/60">
                      <p className="text-xs font-medium text-slate-800 italic dark:text-slate-200">
                        &ldquo;{word.example_sentence}&rdquo;
                      </p>
                      {exampleTrans && (
                        <p className="mt-1.5 border-t border-slate-100 pt-1.5 text-xs text-slate-600 dark:border-slate-800/80 dark:text-slate-400">
                          <span className="font-semibold text-blue-600 dark:text-blue-400 mr-1.5">Dịch nghĩa:</span>
                          {exampleTrans}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
            <div className="pt-2 text-center text-xs text-slate-500">Chạm để lật lại • phím 1-4 để đánh giá</div>
          </div>
        </div>
      </div>

      {flipped ? (
        <div className="space-y-2 pb-8 sm:pb-0">
          <p className="text-center text-xs font-semibold tracking-wider text-slate-500 uppercase dark:text-slate-400">Đánh giá mức độ ghi nhớ (SM-2)</p>
          <div className="grid grid-cols-4 gap-1.5 sm:gap-2">
            {RATINGS.map((item) => (
              <Button
                key={item.value}
                onClick={() => void rate(item.value)}
                disabled={saving}
                variant="outline"
                className={cn("flex h-14 cursor-pointer flex-col justify-center px-1 sm:px-2 py-1 text-center", item.style)}
              >
                <span className="text-xs sm:text-sm font-bold whitespace-nowrap">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : `${item.value}. ${item.label}`}
                </span>
                <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400 sm:hidden">{item.shortHint}</span>
                <span className="hidden sm:inline text-[10px] text-slate-500 dark:text-slate-400 truncate">{item.hint}</span>
              </Button>
            ))}
          </div>
        </div>
      ) : (
        <div className="pb-8 sm:pb-0">
          <Button onClick={() => setFlipped(true)} variant="outline" className="w-full cursor-pointer py-6 text-base font-semibold">
            Lật thẻ xem đáp án
          </Button>
        </div>
      )}

      {pronouncingWord && (
        <PronounceDialog
          open={Boolean(pronouncingWord)}
          onOpenChange={(open) => !open && setPronouncingWord(null)}
          word={pronouncingWord.word}
          expectedIpa={pronouncingWord.ipa}
          meaning={pronouncingWord.meaning}
        />
      )}
    </div>
  );
}
