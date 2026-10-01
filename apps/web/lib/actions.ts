"use client";

import { toast } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import type { ToolExecuteResult } from "@/types";

/** Undo one audited data change (made by the AI mentor or a one-click suggestion). */
export async function undoAction(actionId: number, onDone?: () => void): Promise<boolean> {
  try {
    const result = await api<{ message: string }>(`/ai/actions/${actionId}/undo`, { method: "POST" });
    toast.add({ title: "Đã hoàn tác", description: result.message, type: "success" });
    await refreshLearner();
    onDone?.();
    return true;
  } catch (error) {
    toast.add({ title: "Không hoàn tác được", description: errorMessage(error), type: "error" });
    return false;
  }
}

/** Run an agent tool directly (same validation, audit log and undo as when the AI calls it). */
export async function runTool(
  tool: string,
  args: Record<string, unknown> = {},
  options: { onChanged?: () => void; source?: "coach" | "user" } = {},
): Promise<ToolExecuteResult | null> {
  try {
    const result = await api<ToolExecuteResult>("/ai/actions/execute", {
      method: "POST",
      json: { tool, args, source: options.source ?? "coach" },
    });
    const actionId = result.action_id;
    toast.add({
      title: result.status === "success" ? "Đã áp dụng" : "Không có thay đổi",
      description: result.message,
      type: result.status === "success" ? "success" : "info",
      timeout: actionId ? 8000 : 4000,
      actionProps:
        actionId && result.undoable
          ? { children: "Hoàn tác", onClick: () => void undoAction(actionId, options.onChanged) }
          : undefined,
    });
    await refreshLearner();
    options.onChanged?.();
    return result;
  } catch (error) {
    toast.add({ title: "Không thực hiện được", description: errorMessage(error), type: "error" });
    return null;
  }
}

export const TOOL_LABELS: Record<string, string> = {
  get_learner_overview: "Đọc tổng quan",
  get_skill_report: "Đọc báo cáo kỹ năng",
  get_weekly_report: "Đọc báo cáo tuần",
  search_flashcards: "Tra Sổ tay từ vựng",
  list_error_logs: "Đọc Sổ lỗi",
  get_study_plan: "Đọc kế hoạch học",
  get_lesson: "Đọc bài học",
  find_questions: "Tìm câu hỏi",
  update_learner_profile: "Cập nhật hồ sơ",
  remember_learner_fact: "Ghi nhớ",
  forget_learner_fact: "Quên ghi nhớ",
  create_flashcard: "Thêm thẻ",
  create_flashcards_bulk: "Thêm nhiều thẻ",
  update_flashcard: "Sửa thẻ",
  delete_flashcard: "Xoá thẻ",
  reschedule_flashcard: "Đổi lịch SRS",
  log_error_question: "Lưu câu sai",
  update_error_log: "Sửa Sổ lỗi",
  add_plan_item: "Thêm nhiệm vụ",
  update_plan_item: "Sửa nhiệm vụ",
  replan_week: "Lập lại kế hoạch",
  set_roadmap_task: "Cập nhật mốc lộ trình",
  update_roadmap: "Cập nhật lộ trình",
  create_practice_questions: "Tạo câu luyện",
  add_lesson_note: "Thêm ghi chú bài học",
  add_paraphrase_pair: "Thêm paraphrase",
  schedule_study_reminder: "Đặt lịch nhắc",
  update_reminder: "Sửa lịch nhắc",
  delete_reminder: "Xoá lịch nhắc",
};
