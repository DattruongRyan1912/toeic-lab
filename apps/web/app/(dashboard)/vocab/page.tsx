"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BookOpen, CheckCircle, Clock, Filter, Flame, Layers, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState, LoadingState } from "@/components/states";
import { ParaphraseVault } from "@/modules/vocab/components/paraphrase-vault";
import { AddWordDialog } from "@/modules/vocab/components/add-word-dialog";
import { FlashcardPlayer } from "@/modules/vocab/components/flashcard-player";
import { TopicMatrix } from "@/modules/vocab/components/topic-matrix";
import { WordListTable } from "@/modules/vocab/components/word-list-table";
import { refreshLearner } from "@/lib/learner-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { FlashcardItem, FlashcardSummary, SrsCard } from "@/types";

const TAB = "cursor-pointer px-3 text-slate-600 data-active:bg-blue-600 data-active:text-white dark:text-slate-400 dark:data-active:bg-blue-600 dark:data-active:text-white";

function Metric({ title, value, hint, icon: Icon, tone }: { title: string; value: React.ReactNode; hint: string; icon: typeof BookOpen; tone: string }) {
  return (
    <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-semibold text-slate-500 uppercase dark:text-slate-400">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${tone}`} aria-hidden="true" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${tone}`}>{value}</div>
        <p className="text-[11px] text-slate-500">{hint}</p>
      </CardContent>
    </Card>
  );
}

const TABS = new Set(["review", "topics", "library", "paraphrases"]);

function VocabContent() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const categoryParam = searchParams.get("category");
  const modeParam = searchParams.get("mode");

  const [activeTab, setActiveTab] = useState(tabParam && TABS.has(tabParam) ? tabParam : "review");
  const [selectedCategory, setSelectedCategory] = useState(categoryParam || "all");
  const [studyMode, setStudyMode] = useState<"srs" | "all" | "new">((modeParam as "srs" | "all" | "new") || "srs");

  const words = useApi<FlashcardItem[]>("/flashcards?limit=1000");
  const summary = useApi<FlashcardSummary>("/flashcards/summary");

  const duePath = useMemo(() => {
    const params = new URLSearchParams();
    params.set("limit", "50");
    if (selectedCategory && selectedCategory !== "all") {
      params.set("category", selectedCategory);
    }
    if (studyMode !== "srs") {
      params.set("mode", studyMode);
    }
    return `/flashcards/due?${params.toString()}`;
  }, [selectedCategory, studyMode]);

  const due = useApi<SrsCard[]>(duePath);

  const reloadSummary = summary.reload;
  const onReviewed = useCallback(() => {
    reloadSummary();
    void refreshLearner();
  }, [reloadSummary]);

  const onAdded = (card: FlashcardItem) => {
    words.mutate((prev) => [card, ...(prev ?? [])]);
    summary.reload();
    due.reload();
    void refreshLearner();
  };

  const onDeleted = (id: number) => {
    words.mutate((prev) => prev?.filter((w) => w.id !== id));
    summary.reload();
    due.reload();
    void refreshLearner();
  };

  const handleSelectTopic = (category: string, mode: "srs" | "all" = "srs") => {
    setSelectedCategory(category);
    setStudyMode(mode);
    setActiveTab("review");
  };

  const s = summary.data;
  const categoryList = useMemo(() => {
    if (s?.category_stats && s.category_stats.length > 0) {
      return s.category_stats;
    }
    return Object.entries(s?.categories ?? {}).map(([cat, total]) => ({
      category: cat,
      total,
      due: 0,
      mastered: 0,
      learning: 0,
      new_cards: total,
    }));
  }, [s]);

  const totalInCategory = useMemo(() => {
    if (selectedCategory === "all") return s?.total_cards ?? 0;
    return categoryList.find((c) => c.category === selectedCategory)?.total ?? s?.categories?.[selectedCategory] ?? 0;
  }, [selectedCategory, s, categoryList]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Sổ Tay Từ Vựng & SRS Flashcards</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Học tập chủ động theo từng chủ đề hoặc ôn đúng thẻ đến hạn theo thuật toán SuperMemo-2.
          </p>
        </div>
        <AddWordDialog onWordAdded={onAdded} />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
        <Metric title="Tổng số từ" value={s?.total_cards ?? "…"} hint={`${Object.keys(s?.categories ?? {}).length} chủ đề thương mại`} icon={BookOpen} tone="text-blue-600 dark:text-blue-400" />
        <Metric title="Cần học hôm nay" value={s?.due_cards ?? "…"} hint={s ? `${s.review_due} đến hạn + ${s.new_available} mới` : ""} icon={Clock} tone="text-amber-600 dark:text-amber-400" />
        <Metric title="Đã ôn hôm nay" value={s?.reviewed_today ?? "…"} hint={s ? `${s.learning_cards} thẻ đang trong chu kỳ` : ""} icon={Layers} tone="text-purple-600 dark:text-purple-400" />
        <Metric title="Đã thuộc lòng" value={s?.mastered_cards ?? "…"} hint="≥ 4 lần nhớ hoặc giãn cách ≥ 21 ngày" icon={CheckCircle} tone="text-emerald-600 dark:text-emerald-400" />
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-6">
        <div className="overflow-x-auto no-scrollbar">
          <TabsList className="h-auto w-max sm:w-auto border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900 flex">
            <TabsTrigger value="review" className={TAB}>
              Luyện thẻ SRS ({due.data?.length ?? "…"})
            </TabsTrigger>
            <TabsTrigger value="topics" className={TAB}>
              Chủ đề học tập ({categoryList.length})
            </TabsTrigger>
            <TabsTrigger value="library" className={TAB}>
              Kho từ vựng ({words.data?.length ?? "…"})
            </TabsTrigger>
            <TabsTrigger value="paraphrases" className={TAB}>
              Paraphrase Vault
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Review Player with Topic Selector bar */}
        <TabsContent value="review" className="space-y-4">
          {/* Active Topic Banner / Controller */}
          <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3.5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900/60">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                <Filter className="h-4 w-4" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Chủ đề đang học:</span>
                  <select
                    aria-label="Chọn chủ đề từ vựng"
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="max-w-[170px] sm:max-w-none truncate cursor-pointer rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  >
                    <option value="all">Tất cả chủ đề ({s?.total_cards ?? 621} từ)</option>
                    {categoryList.map((c) => (
                      <option key={c.category} value={c.category}>
                        {c.category} ({c.total} từ)
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mt-0.5 text-[11px] text-slate-500">
                  {selectedCategory === "all"
                    ? `Bao gồm ${categoryList.length} chủ đề TOEIC thương mại`
                    : `${totalInCategory} từ vựng thuộc chủ đề "${selectedCategory}"`}
                </div>
              </div>
            </div>

            {/* Mode Selector */}
            <div className="flex items-center gap-1.5 self-end sm:self-center">
              <button
                type="button"
                onClick={() => setStudyMode("srs")}
                className={cn(
                  "cursor-pointer rounded-lg px-2.5 py-1 text-xs font-medium transition",
                  studyMode === "srs"
                    ? "bg-blue-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400",
                )}
              >
                <Sparkles className="mr-1 inline h-3 w-3" />
                Chuẩn SM-2
              </button>
              <button
                type="button"
                onClick={() => setStudyMode("all")}
                className={cn(
                  "cursor-pointer rounded-lg px-2.5 py-1 text-xs font-medium transition",
                  studyMode === "all"
                    ? "bg-purple-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400",
                )}
                title="Luyện tập tất cả các từ trong chủ đề này không giới hạn bởi hạn ngạch hàng ngày"
              >
                <Flame className="mr-1 inline h-3 w-3" />
                Luyện toàn bộ
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("topics")}
                className="cursor-pointer rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                Xem ma trận chủ đề
              </button>
            </div>
          </div>

          {due.error ? (
            <ErrorState message={due.error} onRetry={due.reload} />
          ) : due.loading || !due.data ? (
            <LoadingState label={`Đang tải thẻ học ${selectedCategory !== "all" ? `chủ đề "${selectedCategory}"` : "đến hạn"}...`} />
          ) : (
            <FlashcardPlayer
              key={`${selectedCategory}-${studyMode}-${due.data.map((c) => c.id).join("-")}`}
              queue={due.data}
              onReviewed={onReviewed}
              onReload={due.reload}
              selectedCategory={selectedCategory}
              studyMode={studyMode}
              onSelectCategory={setSelectedCategory}
              onSwitchMode={setStudyMode}
              totalCardsInCategory={totalInCategory}
            />
          )}
        </TabsContent>

        {/* Tab 2: Topic Matrix */}
        <TabsContent value="topics">
          <TopicMatrix
            stats={categoryList}
            selectedCategory={selectedCategory}
            onSelectTopic={handleSelectTopic}
          />
        </TabsContent>

        {/* Tab 3: Word Library */}
        <TabsContent value="library">
          {words.error ? (
            <ErrorState message={words.error} onRetry={words.reload} />
          ) : words.loading || !words.data ? (
            <LoadingState label="Đang tải kho từ vựng..." />
          ) : (
            <WordListTable
              words={words.data}
              onDeleted={onDeleted}
              onStudyCategory={(cat) => handleSelectTopic(cat, "srs")}
            />
          )}
        </TabsContent>

        {/* Tab 4: Paraphrase Vault */}
        <TabsContent value="paraphrases">
          <ParaphraseVault />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function VocabPage() {
  return (
    <Suspense fallback={<LoadingState label="Đang tải Sổ tay từ vựng..." />}>
      <VocabContent />
    </Suspense>
  );
}
