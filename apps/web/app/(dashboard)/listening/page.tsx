"use client";

import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Headphones,
  Mic,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState, LoadingState } from "@/components/states";
import { trackActivity, useStudyHeartbeat } from "@/lib/heartbeat";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import { ExerciseStudio } from "@/modules/listening/components/exercise-studio";
import type { ListeningExercise } from "@/types";

export default function ListeningStudioPage() {
  const { data: exercises, error, loading, reload } = useApi<ListeningExercise[]>("/listening/exercises?limit=200");
  // Study time on this page (idle-aware, visible tab only) feeds minutes, streak and the plan's listening task.
  useStudyHeartbeat(true, (seconds) => trackActivity("listening", seconds));

  const [selectedPart, setSelectedPart] = useState<string>("all");
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [mode, setMode] = useState<"dictation" | "shadowing">("dictation");

  // Only parts that actually have exercises in the bank (no empty "Part 3" button).
  const parts = [...new Set((exercises ?? []).map((ex) => ex.part))].sort();
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
              <TabsTrigger value="dictation" className="flex items-center gap-1.5 text-xs font-medium px-2.5 sm:px-3">
                <BookOpen className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Chép Chính Tả (Dictation)</span>
                <span className="sm:hidden">Dictation</span>
              </TabsTrigger>
              <TabsTrigger value="shadowing" className="flex items-center gap-1.5 text-xs font-medium px-2.5 sm:px-3">
                <Mic className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Nói Nhại (Shadowing)</span>
                <span className="sm:hidden">Shadowing</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar max-w-full pb-0.5 sm:pb-0 text-xs">
          <span className="mr-1 shrink-0 font-semibold text-slate-500 uppercase">Phần thi:</span>
          {["all", ...parts].map((p) => (
            <Button
              key={p}
              variant={selectedPart === p ? "default" : "outline"}
              size="sm"
              className={cn("h-7 px-3 text-xs font-medium shrink-0", selectedPart === p ? "bg-blue-600 text-white" : "")}
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
          <ExerciseStudio key={`${currentExercise.id}-${mode}`} exercise={currentExercise} mode={mode} />

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
