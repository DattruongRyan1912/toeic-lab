"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bot, CheckCircle2, ImagePlus, Info, Loader2, Search, Send, Sparkles, Undo2, User, X, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/markdown";
import { cn } from "@/lib/utils";
import { TOOL_LABELS, undoAction } from "@/lib/actions";
import { WELCOME_MESSAGE, useMentorStore, type ChatMessage, type SendOptions } from "@/lib/mentor-store";
import type { AIAction } from "@/types";

const VOCAB = { href: "/vocab", label: "Mở Sổ từ vựng" };
const PLAN = { href: "/roadmaps", label: "Xem kế hoạch" };
const ACTION_LINKS: Record<string, { href: string; label: string }> = {
  log_error_question: { href: "/error-log", label: "Mở Sổ lỗi" },
  update_error_log: { href: "/error-log", label: "Mở Sổ lỗi" },
  create_flashcard: VOCAB,
  create_flashcards_bulk: VOCAB,
  update_flashcard: VOCAB,
  reschedule_flashcard: VOCAB,
  add_paraphrase_pair: { href: "/vocab?tab=paraphrases", label: "Xem Paraphrase Vault" },
  schedule_study_reminder: { href: "/settings#reminders", label: "Xem lịch nhắc" },
  update_reminder: { href: "/settings#reminders", label: "Xem lịch nhắc" },
  add_plan_item: PLAN,
  update_plan_item: PLAN,
  replan_week: PLAN,
  set_roadmap_task: PLAN,
  update_roadmap: PLAN,
  update_learner_profile: { href: "/settings#personalization", label: "Xem hồ sơ" },
  remember_learner_fact: { href: "/settings#memories", label: "Xem trí nhớ AI" },
  create_practice_questions: { href: "/mock-tests", label: "Luyện ngay" },
};

function actionLink(action: AIAction) {
  const base = ACTION_LINKS[action.tool];
  const data = action.data ?? {};
  if (typeof data.href === "string" && data.href.startsWith("/")) return { href: data.href, label: base?.label ?? "Mở" };
  if (action.tool === "add_lesson_note" && typeof data.lesson_number === "number") {
    return { href: `/lessons?lesson=${data.lesson_number}`, label: "Xem ghi chú" };
  }
  return base;
}

function ActionChip({ action }: { action: AIAction }) {
  const [busy, setBusy] = useState(false);
  const markUndone = useMentorStore((state) => state.markUndone);
  const label = TOOL_LABELS[action.tool] ?? action.tool;

  if (action.writes === false) {
    // Read-only lookups: a quiet trace of what data the mentor looked at.
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
        <Search className="h-3 w-3" aria-hidden="true" /> Đã đọc: {label}
      </span>
    );
  }

  const link = actionLink(action);
  const ok = action.status === "success" || action.status === "exists";
  const Icon = action.undone ? Undo2 : action.status === "success" ? CheckCircle2 : action.status === "exists" ? Info : XCircle;
  const undo = async () => {
    if (!action.action_id) return;
    setBusy(true);
    if (await undoAction(action.action_id)) markUndone(action.action_id);
    setBusy(false);
  };
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[11px]",
        action.undone
          ? "border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
          : ok
            ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
            : "border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300",
      )}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className={cn("font-medium", action.undone && "line-through")}>
        <span className="font-semibold">{label}:</span> {action.message}
      </span>
      {action.undone ? (
        <span className="ml-auto text-[10px] font-semibold">Đã hoàn tác</span>
      ) : (
        <span className="ml-auto flex items-center gap-2">
          {link && ok && (
            <Link href={link.href} className="font-semibold underline underline-offset-2">
              {link.label}
            </Link>
          )}
          {action.action_id && action.undoable && action.status === "success" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void undo()}
              className="inline-flex cursor-pointer items-center gap-1 font-semibold text-slate-600 underline-offset-2 hover:underline disabled:opacity-50 dark:text-slate-300"
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : <Undo2 className="h-3 w-3" aria-hidden="true" />} Hoàn tác
            </button>
          )}
        </span>
      )}
    </div>
  );
}

export function ChatThread({
  messages,
  sending,
  compact = false,
}: {
  messages: ChatMessage[];
  sending: boolean;
  compact?: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, sending]);

  const shown: ChatMessage[] = messages.length ? messages : [{ id: "welcome", role: "assistant", content: WELCOME_MESSAGE }];
  const avatar = compact ? "h-6 w-6" : "h-8 w-8";
  const icon = compact ? "h-3.5 w-3.5" : "h-4 w-4";

  return (
    <div className={cn("space-y-3.5", compact ? "text-xs" : "text-sm")} aria-live="polite">
      {shown.map((message) => {
        const isUser = message.role === "user";
        return (
          <div key={message.id} className={cn("flex items-start gap-2.5", isUser && "flex-row-reverse")}>
            <div
              className={cn(
                "flex shrink-0 items-center justify-center rounded-full",
                avatar,
                isUser
                  ? "bg-blue-600 text-white"
                  : "border border-blue-200 bg-blue-50 text-blue-600 dark:border-slate-700 dark:bg-slate-800 dark:text-blue-400",
              )}
              aria-hidden="true"
            >
              {isUser ? <User className={icon} /> : <Bot className={icon} />}
            </div>
            <div className={cn("min-w-0 max-w-[85%] space-y-2", isUser && "flex flex-col items-end")}>
              <div
                className={cn(
                  "rounded-2xl px-3.5 py-2.5 leading-relaxed",
                  isUser
                    ? "rounded-tr-none bg-blue-600 whitespace-pre-wrap text-white"
                    : message.error
                      ? "rounded-tl-none border border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
                      : "rounded-tl-none border border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-200",
                )}
              >
                {isUser ? (
                  <>
                    {message.content}
                    {message.hasImage && <span className="mt-1 block text-[10px] opacity-80">📎 Ảnh đính kèm</span>}
                  </>
                ) : (
                  <Markdown className={compact ? "text-xs" : "text-sm"}>{message.content}</Markdown>
                )}
              </div>
              {message.actions?.some((action) => action.writes === false) && (
                <div className="flex flex-wrap gap-1">
                  {message.actions.filter((action) => action.writes === false).map((action, index) => <ActionChip key={`r${index}`} action={action} />)}
                </div>
              )}
              {message.actions?.filter((action) => action.writes !== false).map((action, index) => <ActionChip key={`w${index}`} action={action} />)}
            </div>
          </div>
        );
      })}
      {sending && (
        <div className="flex items-center gap-2.5" role="status">
          <div className={cn("flex items-center justify-center rounded-full border border-blue-200 bg-blue-50 text-blue-600 dark:border-slate-700 dark:bg-slate-800 dark:text-blue-400", avatar)}>
            <Bot className={icon} aria-hidden="true" />
          </div>
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-none border border-slate-200 bg-slate-50 px-3 py-2 text-slate-600 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-400">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" aria-hidden="true" />
            <span>AI Mentor đang phân tích dữ liệu học của bạn...</span>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

export function SuggestionChips({
  items,
  disabled,
  onPick,
}: {
  items: string[];
  disabled: boolean;
  onPick: (value: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="flex gap-1.5 overflow-x-auto">
      {items.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onPick(item)}
          disabled={disabled}
          className="flex shrink-0 cursor-pointer items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] whitespace-nowrap text-slate-700 transition hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700/70 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700/80"
        >
          <Sparkles className="h-2.5 w-2.5 text-blue-600 dark:text-blue-400" aria-hidden="true" />
          <span>{item}</span>
        </button>
      ))}
    </div>
  );
}

const MAX_IMAGE_BYTES = 4 * 1024 * 1024;

export function ChatComposer({
  onSend,
  sending,
  allowImage = false,
  placeholder = "Hỏi về câu hỏi, từ vựng hoặc ngữ pháp...",
  compact = false,
  disabled = false,
  onClick,
}: {
  onSend: (text: string, options?: SendOptions) => void;
  sending: boolean;
  allowImage?: boolean;
  placeholder?: string;
  compact?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  const [text, setText] = useState("");
  const [image, setImage] = useState<{ name: string; data: string } | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (disabled) {
      onClick?.();
      return;
    }
    const value = text.trim() || (image ? "Phân tích câu hỏi trong ảnh đính kèm" : "");
    if (!value || sending) return;
    onSend(value, { imageBase64: image?.data ?? null });
    setText("");
    setImage(null);
  };

  const pickImage = (file: File | undefined) => {
    setImageError(null);
    if (!file) return;
    if (!file.type.startsWith("image/")) return setImageError("Chỉ hỗ trợ file ảnh");
    if (file.size > MAX_IMAGE_BYTES) return setImageError("Ảnh tối đa 4MB");
    const reader = new FileReader();
    reader.onload = () => setImage({ name: file.name, data: String(reader.result) });
    reader.readAsDataURL(file);
  };

  return (
    <div className="space-y-1.5" onClick={disabled ? onClick : undefined}>
      {(image || imageError) && (
        <div className="flex items-center gap-2 text-[11px] text-slate-600 dark:text-slate-400">
          {image && (
            <>
              <span>📎 {image.name}</span>
              <button type="button" onClick={() => setImage(null)} aria-label="Bỏ ảnh đính kèm" className="cursor-pointer text-red-500">
                <X className="h-3 w-3" />
              </button>
            </>
          )}
          {imageError && <span className="text-red-500">{imageError}</span>}
        </div>
      )}
      <form
        className="flex items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        {allowImage && (
          <>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => pickImage(e.target.files?.[0])} />
            <Button
              type="button"
              variant="outline"
              size={compact ? "icon-sm" : "icon"}
              onClick={() => fileRef.current?.click()}
              disabled={sending || disabled}
              aria-label="Đính kèm ảnh đề thi"
              className="shrink-0 cursor-pointer"
            >
              <ImagePlus className="h-4 w-4" />
            </Button>
          </>
        )}
        <label className="sr-only" htmlFor={compact ? "mentor-input-widget" : "mentor-input"}>
          Tin nhắn cho AI Mentor
        </label>
        <textarea
          id={compact ? "mentor-input-widget" : "mentor-input"}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder={placeholder}
          disabled={sending || disabled}
          onClick={disabled ? onClick : undefined}
          className={cn(
            "field-sizing-content max-h-32 min-h-9 flex-1 resize-none rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none placeholder:text-slate-400 focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/30 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100",
            disabled && "cursor-pointer bg-slate-100/70 dark:bg-slate-900/40",
            compact ? "text-xs" : "text-sm",
          )}
        />
        <Button
          type="submit"
          disabled={!disabled && (sending || (!text.trim() && !image))}
          onClick={disabled ? onClick : undefined}
          className={cn("shrink-0 cursor-pointer bg-blue-600 text-white hover:bg-blue-500", compact ? "h-9 px-3" : "h-10 px-4")}
          aria-label="Gửi"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </form>
    </div>
  );
}
