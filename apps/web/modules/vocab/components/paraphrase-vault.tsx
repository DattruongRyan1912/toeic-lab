"use client";

import { useState } from "react";
import { ArrowLeftRight, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErrorState, LoadingState } from "@/components/states";
import { askMentor } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import type { ParaphrasePair } from "@/types";

export function ParaphraseVault() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const pairs = useApi<ParaphrasePair[]>(`/knowledge/paraphrases?limit=300${submitted ? `&query=${encodeURIComponent(submitted)}` : ""}`);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <form
          className="flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted(query.trim());
          }}
        >
          <label className="sr-only" htmlFor="pp-search">Tìm paraphrase</label>
          <Input id="pp-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="postpone, deadline..." className="h-9 w-60" />
          <Button type="submit" size="sm" variant="outline" className="cursor-pointer">
            <Search className="h-3.5 w-3.5" aria-hidden="true" /> Tìm
          </Button>
        </form>
        <Button
          size="sm"
          variant="outline"
          className="cursor-pointer"
          onClick={() =>
            askMentor("Dựa trên các câu tôi làm sai gần đây, thêm 5 cặp paraphrase TOEIC hay gặp (từ trong bài ↔ từ trong đáp án) vào Paraphrase Vault của tôi, mỗi cặp kèm ví dụ ngắn.", { pageContext: "/vocab" })
          }
        >
          <Sparkles className="h-3.5 w-3.5 text-purple-500" aria-hidden="true" /> Nhờ AI bổ sung từ câu sai
        </Button>
      </div>

      {pairs.error ? (
        <ErrorState message={pairs.error} onRetry={pairs.reload} />
      ) : !pairs.data ? (
        <LoadingState label="Đang tải Paraphrase Vault..." />
      ) : pairs.data.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500 dark:border-slate-700">
          {submitted ? `Không có cặp nào khớp “${submitted}”.` : "Chưa có cặp paraphrase nào. Nhờ AI Mentor thêm, hoặc lưu khi chữa câu sai."}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] text-slate-500 uppercase dark:bg-slate-900/60">
              <tr>
                <th className="p-3">Trong bài đọc/nghe</th>
                <th className="p-3" aria-label="tương đương" />
                <th className="p-3">Trong đáp án</th>
                <th className="p-3">Nghĩa & ví dụ</th>
                <th className="p-3">Part</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
              {pairs.data.map((pair) => (
                <tr key={pair.id} className="align-top">
                  <td className="p-3 font-semibold text-slate-900 dark:text-white">{pair.word_in_text}</td>
                  <td className="p-3 text-slate-400"><ArrowLeftRight className="h-3.5 w-3.5" aria-hidden="true" /></td>
                  <td className="p-3 font-semibold text-emerald-700 dark:text-emerald-400">{pair.word_in_answer}</td>
                  <td className="p-3 text-slate-600 dark:text-slate-400">
                    {pair.meaning}
                    {pair.context_example && <span className="mt-0.5 block italic text-slate-500">{pair.context_example}</span>}
                  </td>
                  <td className="p-3 whitespace-nowrap text-slate-500">{pair.part_target ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
