"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Bot, Download, Filter, Loader2, Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { ERROR_TYPES, SOURCE_LABELS, STATUS_LABELS, STATUS_STYLES, formatDate, lessonHref } from "@/lib/format";
import { refreshLearner, useLearnerStore } from "@/lib/learner-store";
import { askMentor } from "@/lib/mentor-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { ErrorLogEntry, ErrorStatus, ErrorType, MockTestItem, TestQuestionItem } from "@/types";

const PARTS = ["Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6", "Part 7"];
const NEXT_STATUS: Record<ErrorStatus, ErrorStatus> = { unresolved: "reviewed", reviewed: "mastered", mastered: "unresolved" };
const SELECT = "w-full rounded-lg border border-input bg-transparent p-2 text-xs text-slate-800 dark:bg-input/30 dark:text-slate-200";

function csvCell(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function exportCsv(logs: ErrorLogEntry[]) {
  // Same columns as templates/error_log_template.csv (+ Topic/Source/Created_At)
  const header = ["Test_ID", "Part", "Question_No", "Error_Type", "My_Choice", "Correct_Choice", "Question_Summary", "Root_Cause", "Paraphrase_Or_KeyRule", "Status", "Topic", "Source", "Created_At"];
  const rows = logs.map((l) => [l.test_id, l.part, l.question_no, l.error_type, l.user_choice, l.correct_choice, l.question_content, l.root_cause, l.key_rule_or_paraphrase, l.status, l.topic, l.source, l.created_at]);
  const csv = "\uFEFF" + [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `TOEIC_Error_Log_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function NewErrorForm({ tests, onCreated }: { tests: MockTestItem[]; onCreated: (log: ErrorLogEntry) => void }) {
  const [testId, setTestId] = useState(tests[0]?.test_id ?? "Practice");
  const [part, setPart] = useState("Part 5");
  const [questionNo, setQuestionNo] = useState("");
  const [errorType, setErrorType] = useState<ErrorType>("GRAMMAR");
  const [userChoice, setUserChoice] = useState("");
  const [correctChoice, setCorrectChoice] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [keyRule, setKeyRule] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const number = Number(questionNo);
  const lookupPath = testId !== "Practice" && Number.isInteger(number) && number > 0 ? `/tests/${encodeURIComponent(testId)}/questions/${number}` : null;
  const bank = useApi<TestQuestionItem>(lookupPath);
  const match = lookupPath && bank.data && bank.data.question_no === number && bank.data.test_id === testId ? bank.data : null;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!rootCause.trim()) return setError("Hãy ghi nguyên nhân gốc — đây là phần quan trọng nhất của RCA.");
    setSubmitting(true);
    try {
      const created = await api<ErrorLogEntry>("/error-logs", {
        method: "POST",
        json: {
          test_id: testId,
          part: match?.part ?? part,
          question_no: questionNo ? number : null,
          question_id: match?.id ?? null,
          error_type: errorType,
          user_choice: userChoice || null,
          correct_choice: correctChoice || null,
          root_cause: rootCause.trim(),
          key_rule_or_paraphrase: keyRule.trim() || null,
        },
      });
      onCreated(created);
      setRootCause("");
      setKeyRule("");
      setUserChoice("");
      setCorrectChoice("");
      setQuestionNo("");
      toast.add({ title: "Đã thêm vào Sổ lỗi", description: created.topic ? `Gắn với lỗ hổng "${created.topic}"` : undefined, type: "success" });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
        <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
          <Plus className="h-4 w-4 text-blue-500" aria-hidden="true" /> Nhập câu sai mới
        </CardTitle>
        <p className="text-[11px] text-slate-500">Câu làm trong phòng thi thử được ghi tự động. Form này dành cho đề giấy / nguồn ngoài.</p>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={submit} className="space-y-4">
          {error && (
            <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
              {error}
            </p>
          )}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div className="space-y-1">
              <Label htmlFor="el-test" className="text-xs">Đề thi</Label>
              <select id="el-test" value={testId} onChange={(e) => setTestId(e.target.value)} className={SELECT}>
                {tests.map((t) => (
                  <option key={t.test_id} value={t.test_id}>{t.test_id}</option>
                ))}
                <option value="Practice">Nguồn khác</option>
              </select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="el-part" className="text-xs">Phần thi</Label>
              <select id="el-part" value={match?.part ?? part} disabled={Boolean(match)} onChange={(e) => setPart(e.target.value)} className={SELECT}>
                {PARTS.map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="el-no" className="text-xs">Số câu</Label>
              <Input id="el-no" type="number" min={1} max={200} value={questionNo} onChange={(e) => setQuestionNo(e.target.value)} className="text-xs" placeholder="VD: 108" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="el-type" className="text-xs">Mã lỗi RCA</Label>
              <select id="el-type" value={errorType} onChange={(e) => setErrorType(e.target.value as ErrorType)} className={SELECT}>
                {ERROR_TYPES.map((t) => (
                  <option key={t.key} value={t.key}>{t.key}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="el-mine" className="text-xs">Bạn chọn</Label>
              <select id="el-mine" value={userChoice} onChange={(e) => setUserChoice(e.target.value)} className={SELECT}>
                <option value="">—</option>
                {["A", "B", "C", "D"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="el-correct" className="text-xs">Đáp án đúng</Label>
              <select id="el-correct" value={match ? match.correct_choice : correctChoice} disabled={Boolean(match)} onChange={(e) => setCorrectChoice(e.target.value)} className={SELECT}>
                <option value="">—</option>
                {["A", "B", "C", "D"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {match && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200">
              <p className="font-semibold">📚 Tìm thấy trong ngân hàng đề — đáp án, Part và tag bẫy sẽ được điền tự động:</p>
              <p className="mt-1">{match.sentence}</p>
              <p className="mt-1">
                Đáp án ({match.correct_choice}) • Gợi ý mã lỗi: <strong>{match.error_type}</strong>
                {match.trap_tag ? ` • ${match.trap_tag}` : ""}
                {match.error_type !== errorType && (
                  <button type="button" className="ml-2 cursor-pointer font-semibold underline" onClick={() => setErrorType(match.error_type)}>
                    Dùng {match.error_type}
                  </button>
                )}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="el-cause" className="text-xs">Nguyên nhân gốc (Root Cause) *</Label>
              <Textarea id="el-cause" rows={2} placeholder="VD: Tưởng chỗ trống trước động từ cần tính từ, quên quy tắc S + [ADV] + V" value={rootCause} onChange={(e) => setRootCause(e.target.value)} className="text-xs" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="el-rule" className="text-xs">Quy tắc nhớ / Cặp paraphrase</Label>
              <Textarea id="el-rule" rows={2} placeholder="VD: S + [ADV] + V_chính + O" value={keyRule} onChange={(e) => setKeyRule(e.target.value)} className="text-xs" />
            </div>
          </div>
          <div className="flex justify-end">
            <Button type="submit" disabled={submitting} className="flex cursor-pointer items-center gap-1.5 bg-red-600 px-5 text-xs text-white hover:bg-red-500">
              {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Plus className="h-3.5 w-3.5" aria-hidden="true" />} Thêm vào Sổ lỗi
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function ErrorRow({ log, onChanged, onDeleted }: { log: ErrorLogEntry; onChanged: (log: ErrorLogEntry) => void; onDeleted: (id: number) => void }) {
  const [editing, setEditing] = useState(false);
  const [rootCause, setRootCause] = useState(log.root_cause);
  const [keyRule, setKeyRule] = useState(log.key_rule_or_paraphrase ?? "");
  const [busy, setBusy] = useState(false);
  const [nowIso] = useState(() => new Date().toISOString()); // naive-UTC API timestamps compare as strings

  const patch = async (body: Record<string, unknown>, success?: string) => {
    setBusy(true);
    try {
      const updated = await api<ErrorLogEntry>(`/error-logs/${log.id}`, { method: "PATCH", json: body });
      onChanged(updated);
      if (success) toast.add({ title: success, type: "success" });
      return true;
    } catch (err) {
      toast.add({ title: "Không cập nhật được", description: errorMessage(err), type: "error" });
      return false;
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Xóa câu này khỏi Sổ lỗi?")) return;
    setBusy(true);
    try {
      await api(`/error-logs/${log.id}`, { method: "DELETE" });
      onDeleted(log.id);
    } catch (err) {
      toast.add({ title: "Không xóa được", description: errorMessage(err), type: "error" });
      setBusy(false);
    }
  };

  const ask = () =>
    askMentor(
      log.question_id
        ? `Tôi chọn (${log.user_choice ?? "?"}) nhưng đáp án là (${log.correct_choice}). Nguyên nhân tôi ghi: "${log.root_cause}". Phân tích lại và cho tôi quy tắc tránh lặp lại.`
        : `Tôi sai một câu ${log.part} [${log.error_type}]: "${log.question_content ?? log.root_cause}". Phân tích nguyên nhân gốc và cách khắc phục.`,
      { questionId: log.question_id, pageContext: "/error-log" },
    );

  return (
    <tr className="align-top transition hover:bg-slate-50 dark:hover:bg-slate-900/40">
      <td className="p-3 whitespace-nowrap">
        <p className="font-semibold text-slate-900 dark:text-white">{log.test_id}</p>
        <p className="text-[11px] text-blue-600 dark:text-blue-400">
          {log.part}
          {log.question_no ? ` - Câu ${log.question_no}` : ""}
        </p>
        <p className="mt-0.5 text-[10px] text-slate-500">
          {SOURCE_LABELS[log.source ?? "manual"] ?? log.source} • {formatDate(log.created_at)}
        </p>
      </td>
      <td className="p-3">
        <select
          aria-label="Mã lỗi RCA"
          value={log.error_type}
          disabled={busy}
          onChange={(e) => void patch({ error_type: e.target.value })}
          className="rounded border border-red-200 bg-red-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-red-700 dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-400"
        >
          {ERROR_TYPES.map((t) => (
            <option key={t.key} value={t.key}>{t.key}</option>
          ))}
        </select>
        {log.topic && <p className="mt-1 max-w-[10rem] text-[10px] text-slate-500">{log.topic}</p>}
      </td>
      <td className="p-3 text-center whitespace-nowrap">
        <span className="mr-1 font-bold text-red-500 line-through">{log.user_choice ?? "—"}</span>➔
        <span className="ml-1 font-bold text-emerald-600 dark:text-emerald-400">{log.correct_choice ?? "—"}</span>
      </td>
      <td className="max-w-md p-3">
        {editing ? (
          <div className="space-y-2">
            <Textarea aria-label="Nguyên nhân gốc" rows={2} value={rootCause} onChange={(e) => setRootCause(e.target.value)} className="text-xs" />
            <Textarea aria-label="Quy tắc nhớ" rows={2} value={keyRule} onChange={(e) => setKeyRule(e.target.value)} className="text-xs" placeholder="Quy tắc nhớ / paraphrase" />
            <div className="flex gap-2">
              <Button
                size="sm"
                disabled={busy || !rootCause.trim()}
                className="h-7 cursor-pointer text-xs"
                onClick={() => void patch({ root_cause: rootCause.trim(), key_rule_or_paraphrase: keyRule.trim() || null }, "Đã lưu phân tích").then((ok) => ok && setEditing(false))}
              >
                Lưu
              </Button>
              <Button size="sm" variant="ghost" className="h-7 cursor-pointer text-xs" onClick={() => setEditing(false)}>
                Hủy
              </Button>
            </div>
          </div>
        ) : (
          <>
            {log.question_content && <p className="mb-1 text-[11px] text-slate-500 italic">{log.question_content}</p>}
            <p className="font-medium text-slate-800 dark:text-slate-200">{log.root_cause}</p>
            {log.key_rule_or_paraphrase && <p className="mt-1 font-mono text-[11px] text-purple-700 dark:text-purple-300">{log.key_rule_or_paraphrase}</p>}
          </>
        )}
      </td>
      <td className="p-3 text-center">
        <button
          type="button"
          disabled={busy}
          onClick={() => void patch({ status: NEXT_STATUS[log.status] })}
          title="Bấm để chuyển trạng thái"
          className={cn("cursor-pointer rounded-full border px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap", STATUS_STYLES[log.status])}
        >
          {STATUS_LABELS[log.status]}
        </button>
        {log.review_count > 0 && <p className="mt-1 text-[10px] text-slate-500">ôn {log.review_count} lần</p>}
        {log.status !== "mastered" && log.question_id && (
          <p className="mt-1 text-[10px] whitespace-nowrap text-slate-500" title="Lịch ôn câu sai: 1 → 3 → 7 ngày, đúng 3 lần đúng hạn là nắm chắc">
            Bậc {Math.min(log.review_stage ?? 0, 3)}/3 •{" "}
            {log.next_review_at && log.next_review_at > nowIso ? `ôn ${formatDate(log.next_review_at)}` : <strong className="text-red-500">đến hạn ôn</strong>}
          </p>
        )}
      </td>
      <td className="p-3">
        <div className="flex flex-col items-start gap-1 text-[11px] font-semibold">
          <button type="button" onClick={ask} className="flex cursor-pointer items-center gap-1 text-purple-600 hover:underline dark:text-purple-400">
            <Bot className="h-3 w-3" aria-hidden="true" /> Hỏi AI
          </button>
          {log.lesson_number && (
            <Link href={lessonHref(log.lesson_number)} className="text-blue-600 hover:underline dark:text-blue-400">
              Ôn Bài {String(log.lesson_number).padStart(2, "0")}
            </Link>
          )}
          <button type="button" onClick={() => setEditing(true)} className="flex cursor-pointer items-center gap-1 text-slate-600 hover:underline dark:text-slate-400">
            <Pencil className="h-3 w-3" aria-hidden="true" /> Sửa RCA
          </button>
          <button type="button" onClick={() => void remove()} disabled={busy} className="flex cursor-pointer items-center gap-1 text-red-500 hover:underline">
            <Trash2 className="h-3 w-3" aria-hidden="true" /> Xóa
          </button>
        </div>
      </td>
    </tr>
  );
}

function ErrorLogContent() {
  const searchParams = useSearchParams();
  const logs = useApi<ErrorLogEntry[]>("/error-logs");
  const tests = useApi<MockTestItem[]>("/tests");
  const [typeFilter, setTypeFilter] = useState(searchParams.get("type")?.toUpperCase() ?? "ALL");
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") ?? "open");
  const [sourceFilter, setSourceFilter] = useState(searchParams.get("source") ?? "all");

  const changed = (updated: ErrorLogEntry) => {
    logs.mutate((prev) => prev?.map((l) => (l.id === updated.id ? updated : l)));
    void refreshLearner();
  };
  const created = (entry: ErrorLogEntry) => {
    logs.mutate((prev) => [entry, ...(prev ?? [])]);
    void refreshLearner();
  };
  const deleted = (id: number) => {
    logs.mutate((prev) => prev?.filter((l) => l.id !== id));
    void refreshLearner();
  };

  const all = logs.data ?? [];
  const filtered = all.filter(
    (l) =>
      (typeFilter === "ALL" || l.error_type === typeFilter) &&
      (statusFilter === "all" || (statusFilter === "open" ? l.status !== "mastered" : l.status === statusFilter)) &&
      (sourceFilter === "all" || (l.source ?? "manual") === sourceFilter),
  );
  const openCount = all.filter((l) => l.status !== "mastered").length;
  const dueCount = useLearnerStore((state) => state.stats?.error_reviews_due ?? 0);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-red-200 bg-gradient-to-r from-red-50/80 via-white to-amber-50/60 p-6 md:flex-row md:items-center md:p-8 dark:border-red-500/20 dark:from-red-950/40 dark:via-slate-900 dark:to-amber-950/40">
        <div>
          <span className="rounded-full border border-red-200 bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-700 dark:border-red-500/30 dark:bg-red-500/20 dark:text-red-400">
            DATA-DRIVEN ERROR LOG
          </span>
          <h1 className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Sổ Tay Lỗi Sai (RCA)</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-400">
            {openCount} câu chưa khắc phục / {all.length} tổng. Câu sai quay lại theo lịch 1 → 3 → 7 ngày; làm đúng đủ 3 lần đúng hạn sẽ tự chuyển <strong>Đã nắm chắc</strong> và lỗ hổng tự đóng.
          </p>
          {dueCount > 0 && (
            <Link href="/mock-tests?mode=review" className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500">
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Ôn {dueCount} câu đến hạn
            </Link>
          )}
        </div>
        <Button onClick={() => exportCsv(filtered)} disabled={!filtered.length} variant="outline" className="flex shrink-0 self-start sm:self-auto cursor-pointer items-center gap-2">
          <Download className="h-4 w-4 text-emerald-500" aria-hidden="true" /> Xuất CSV ({filtered.length})
        </Button>
      </div>

      {tests.data && <NewErrorForm tests={tests.data} onCreated={created} />}

      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
        {["ALL", ...ERROR_TYPES.map((t) => t.key)].map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setTypeFilter(type)}
            className={cn(
              "cursor-pointer rounded-full border px-3 py-1 text-xs font-medium whitespace-nowrap transition",
              typeFilter === type
                ? "border-red-300 bg-red-100 font-bold text-red-700 dark:border-red-500/40 dark:bg-red-500/20 dark:text-red-400"
                : "border-slate-200 bg-white text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400",
            )}
          >
            {type === "ALL" ? "Tất cả mã" : type} ({type === "ALL" ? all.length : all.filter((l) => l.error_type === type).length})
          </button>
        ))}
        <label className="sr-only" htmlFor="status-filter">Lọc trạng thái</label>
        <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="ml-auto rounded-lg border border-slate-200 bg-white p-1.5 text-xs dark:border-slate-700 dark:bg-slate-900">
          <option value="open">Chưa nắm chắc</option>
          <option value="all">Mọi trạng thái</option>
          <option value="unresolved">Chưa khắc phục</option>
          <option value="reviewed">Đã xem lại</option>
          <option value="mastered">Đã nắm chắc</option>
        </select>
        <label className="sr-only" htmlFor="source-filter">Lọc nguồn</label>
        <select id="source-filter" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white p-1.5 text-xs dark:border-slate-700 dark:bg-slate-900">
          <option value="all">Mọi nguồn</option>
          <option value="mock_test">Thi thử</option>
          <option value="ai_mentor">AI Mentor</option>
          <option value="manual">Tự nhập</option>
        </select>
      </div>

      <Card className="overflow-hidden border-slate-200 bg-white p-0 dark:border-slate-700/70 dark:bg-slate-800/80">
        {logs.error ? (
          <div className="p-6">
            <ErrorState message={logs.error} onRetry={logs.reload} />
          </div>
        ) : logs.loading ? (
          <LoadingState label="Đang tải Sổ lỗi..." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-400">
                <tr>
                  <th className="p-3">Đề & câu</th>
                  <th className="p-3">Mã RCA</th>
                  <th className="p-3 text-center">Sai / Đúng</th>
                  <th className="p-3">Nguyên nhân gốc & quy tắc</th>
                  <th className="p-3 text-center">Trạng thái</th>
                  <th className="p-3">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      Không có câu sai nào trong bộ lọc này.{" "}
                      <Link href="/mock-tests" className="font-semibold text-blue-600 dark:text-blue-400">Làm bài luyện</Link> để hệ thống tự ghi lỗi.
                    </td>
                  </tr>
                ) : (
                  filtered.map((log) => <ErrorRow key={`${log.id}-${log.status}-${log.root_cause}`} log={log} onChanged={changed} onDeleted={deleted} />)
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function ErrorLogPage() {
  return (
    <Suspense fallback={<LoadingState label="Đang tải Sổ lỗi..." />}>
      <ErrorLogContent />
    </Suspense>
  );
}
