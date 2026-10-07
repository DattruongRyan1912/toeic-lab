"use client";

import { useMemo, useState } from "react";
import { Filter, Mic, Play, Search, Trash2, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { EmptyState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { speak } from "@/lib/audio";
import { ipa } from "@/lib/format";
import { cn } from "@/lib/utils";
import { renderHighlightedSentence } from "@/lib/vocab-utils";
import type { FlashcardItem } from "@/types";
import { PronounceDialog } from "./pronounce-dialog";

interface WordListTableProps {
  words: FlashcardItem[];
  onDeleted: (id: number) => void;
  onStudyCategory?: (category: string) => void;
}

export function WordListTable({ words, onDeleted, onStudyCategory }: WordListTableProps) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [pronouncingWord, setPronouncingWord] = useState<FlashcardItem | null>(null);
  const isAdmin = useAuthStore((state) => state.user?.role === "admin"); // the deck is shared: only admins delete

  const categories = useMemo(() => ["all", ...Array.from(new Set(words.map((w) => w.category).filter(Boolean))).sort()], [words]);
  const term = search.trim().toLowerCase();
  const filtered = words.filter((w) => {
    const matches =
      !term ||
      w.word.toLowerCase().includes(term) ||
      w.meaning.toLowerCase().includes(term) ||
      (w.collocations ?? "").toLowerCase().includes(term) ||
      (w.paraphrase_pair ?? "").toLowerCase().includes(term);
    return matches && (category === "all" || w.category === category);
  });

  const remove = async (item: FlashcardItem) => {
    if (!window.confirm(`Xóa từ "${item.word}" khỏi bộ thẻ dùng chung? Lịch sử ôn của từ này ở MỌI học viên cũng bị xóa.`)) return;
    setDeletingId(item.id);
    try {
      await api(`/flashcards/${item.id}`, { method: "DELETE" });
      onDeleted(item.id);
      toast.add({ title: `Đã xóa "${item.word}"`, type: "success" });
    } catch (error) {
      toast.add({ title: "Không xóa được từ", description: errorMessage(error), type: "error" });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
        <div className="relative w-full sm:w-72">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <Input
            aria-label="Tìm từ vựng"
            placeholder="Tìm theo từ, nghĩa, collocation..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex w-full items-center gap-2 overflow-x-auto pb-1 sm:w-auto sm:pb-0">
          <Filter className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategory(cat)}
              className={cn(
                "cursor-pointer rounded-full border px-3 py-1 text-xs whitespace-nowrap transition",
                category === cat
                  ? "border-blue-300 bg-blue-50 font-semibold text-blue-700 dark:border-blue-500/40 dark:bg-blue-600/20 dark:text-blue-400"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400",
              )}
            >
              {cat === "all" ? `Tất cả (${words.length})` : cat}
            </button>
          ))}
          {category !== "all" && onStudyCategory && (
            <Button
              type="button"
              size="sm"
              variant="default"
              onClick={() => onStudyCategory(category)}
              className="h-7 cursor-pointer text-xs shrink-0 ml-1"
            >
              <Play className="mr-1 h-3 w-3" /> Học chủ đề này ({filtered.length})
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-3">
        {filtered.length === 0 ? (
          <EmptyState title="Không tìm thấy từ vựng phù hợp" />
        ) : (
          filtered.map((item) => (
            <div
              key={item.id}
              className="group flex flex-col justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 transition hover:border-slate-300 md:flex-row md:items-center dark:border-slate-800/80 dark:bg-slate-900/60 dark:hover:border-slate-700"
            >
              <div className="flex-1 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-lg font-bold text-slate-900 transition group-hover:text-blue-600 dark:text-white dark:group-hover:text-blue-400">{item.word}</span>
                  {item.ipa && <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">{ipa(item.ipa)}</span>}
                  {item.word_type && <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">[{item.word_type}]</span>}
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800/60">{item.category}</span>
                </div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{item.meaning}</p>
                {(item.collocations || item.paraphrase_pair) && (
                  <div className="flex flex-wrap gap-2 pt-1 text-xs">
                    {item.collocations && (
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-800/80 dark:text-slate-400">
                        <strong className="text-purple-600 dark:text-purple-400">Collocations:</strong> {item.collocations}
                      </span>
                    )}
                    {item.paraphrase_pair && (
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-800/80 dark:text-slate-400">
                        <strong className="text-emerald-600 dark:text-emerald-400">Paraphrase:</strong> {item.paraphrase_pair}
                      </span>
                    )}
                  </div>
                )}
                {item.example_sentence && (
                  <div className="mt-1.5 rounded-lg border border-slate-100 bg-slate-50/80 p-2 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                    <p className="font-medium text-slate-700 italic dark:text-slate-300">
                      &ldquo;{renderHighlightedSentence(item.example_sentence, item.word)}&rdquo;
                    </p>
                    {item.example_translation && (
                      <p className="mt-1 border-t border-slate-200/60 pt-1 text-slate-500 dark:border-slate-700/50 dark:text-slate-400">
                        <span className="font-semibold text-blue-600 dark:text-blue-400 mr-1">Dịch:</span>
                        {item.example_translation}
                      </p>
                    )}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2 self-end md:self-center">
                <Button size="sm" variant="outline" onClick={() => void speak(item.word)} className="h-8 cursor-pointer px-2.5" aria-label={`Nghe phát âm ${item.word}`} title="Nghe phát âm mẫu">
                  <Volume2 className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPronouncingWord(item)}
                  className="h-8 cursor-pointer px-2.5 text-blue-600 hover:text-blue-700 dark:text-blue-400"
                  aria-label={`Luyện phát âm ${item.word} với AI`}
                  title="Luyện phát âm với AI"
                >
                  <Mic className="h-4 w-4" />
                </Button>
                {isAdmin && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={deletingId === item.id}
                    onClick={() => void remove(item)}
                    className="h-8 cursor-pointer px-2.5 hover:text-red-500"
                    aria-label={`Xóa ${item.word}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

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
