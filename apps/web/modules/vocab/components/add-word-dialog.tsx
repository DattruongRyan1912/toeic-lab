"use client";

import { useState } from "react";
import { Check, Loader2, Plus, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { useLearnerStore } from "@/lib/learner-store";
import type { FlashcardItem } from "@/types";

interface AddWordDialogProps {
  onWordAdded: (word: FlashcardItem) => void;
}

const EMPTY = { word: "", ipa: "", wordType: "", category: "General Business", meaning: "", collocations: "", paraphrase: "", example: "" };

export function AddWordDialog({ onWordAdded }: AddWordDialogProps) {
  const aiOffline = useLearnerStore((state) => state.aiStatus?.offline ?? false);
  const [open, setOpen] = useState(false);
  const [loadingAi, setLoadingAi] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY);

  const update = (key: keyof typeof EMPTY) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const autoFill = async () => {
    if (!form.word.trim()) return setError("Nhập từ vựng trước khi dùng AI Auto-Fill");
    setError(null);
    setLoadingAi(true);
    try {
      const data = await api<{
        word: string;
        ipa: string;
        word_type: string;
        category: string;
        meaning: string;
        collocations: string;
        paraphrase_pair: string;
        example_sentence: string;
      }>("/flashcards/ai-fill", { method: "POST", json: { word: form.word.trim() } });
      setForm({
        word: data.word || form.word,
        ipa: data.ipa,
        wordType: data.word_type,
        category: data.category || form.category,
        meaning: data.meaning,
        collocations: data.collocations,
        paraphrase: data.paraphrase_pair,
        example: data.example_sentence,
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingAi(false);
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.word.trim() || !form.meaning.trim() || !form.example.trim()) {
      return setError("Cần nhập Từ vựng, Nghĩa và Câu ví dụ (SRS học tốt nhất theo ngữ cảnh).");
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await api<FlashcardItem>("/flashcards", {
        method: "POST",
        json: {
          word: form.word.trim(),
          ipa: form.ipa.trim() || null,
          word_type: form.wordType.trim() || null,
          category: form.category.trim() || "General Business",
          meaning: form.meaning.trim(),
          collocations: form.collocations.trim() || null,
          paraphrase_pair: form.paraphrase.trim() || null,
          example_sentence: form.example.trim(),
        },
      });
      onWordAdded(created);
      toast.add({ title: `Đã thêm "${created.word}"`, description: "Thẻ mới sẽ xuất hiện trong phiên ôn SRS.", type: "success" });
      setForm(EMPTY);
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button className="flex cursor-pointer items-center gap-2 bg-blue-600 text-white hover:bg-blue-500" />}>
        <Plus className="h-4 w-4" aria-hidden="true" /> Thêm từ vựng mới
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-bold">
            Thêm từ vựng vào Sổ tay
            <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-normal text-blue-700 dark:border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400">
              {aiOffline ? "AI offline" : "AI Powered"}
            </span>
          </DialogTitle>
        </DialogHeader>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="mt-2 space-y-4">
          <div className="space-y-1">
            <Label htmlFor="word">Từ vựng tiếng Anh *</Label>
            <div className="flex gap-2">
              <Input id="word" placeholder="VD: postpone, accommodate, invoice..." value={form.word} onChange={update("word")} required />
              <Button
                type="button"
                variant="secondary"
                onClick={() => void autoFill()}
                disabled={loadingAi || !form.word.trim() || aiOffline}
                title={aiOffline ? "Cần cấu hình API key AI trên server (.env)" : undefined}
                className="flex shrink-0 cursor-pointer items-center gap-1.5"
              >
                {loadingAi ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Sparkles className="h-4 w-4 text-purple-500" aria-hidden="true" />}
                {loadingAi ? "Đang tạo..." : "AI Auto-Fill"}
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              {aiOffline
                ? "AI chưa được cấu hình trên server — hãy nhập thủ công."
                : "AI tự sinh IPA, collocation, paraphrase và câu ví dụ chuẩn TOEIC. Hãy kiểm tra lại trước khi lưu."}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="ipa">Phiên âm IPA</Label>
              <Input id="ipa" placeholder="pəʊstˈpəʊn" value={form.ipa} onChange={update("ipa")} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="wordType">Từ loại</Label>
              <Input id="wordType" placeholder="verb, noun, adjective..." value={form.wordType} onChange={update("wordType")} />
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="category">Chủ đề</Label>
            <Input id="category" placeholder="General Business, Finance & Banking..." value={form.category} onChange={update("category")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="meaning">Nghĩa tiếng Việt *</Label>
            <Input id="meaning" placeholder="hoãn lại, dời lịch..." value={form.meaning} onChange={update("meaning")} required />
          </div>
          <div className="space-y-1">
            <Label htmlFor="collocations">Collocations</Label>
            <Input id="collocations" placeholder="postpone a meeting, postpone indefinitely" value={form.collocations} onChange={update("collocations")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="paraphrase">Paraphrase Vault</Label>
            <Input id="paraphrase" placeholder="postpone = delay = put off = defer" value={form.paraphrase} onChange={update("paraphrase")} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="example">Câu ví dụ chuẩn đề thi *</Label>
            <Textarea id="example" rows={2} placeholder="The board decided to postpone the meeting until next week." value={form.example} onChange={update("example")} required />
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-3 dark:border-slate-800">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} className="cursor-pointer">
              Hủy
            </Button>
            <Button type="submit" disabled={submitting} className="flex cursor-pointer items-center gap-2 bg-blue-600 text-white hover:bg-blue-500">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Check className="h-4 w-4" aria-hidden="true" />}
              {submitting ? "Đang lưu..." : "Lưu từ vựng"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
