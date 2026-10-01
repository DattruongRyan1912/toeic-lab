"use client";

import { useState } from "react";
import { Check, Loader2, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { Chip, PARTS, StylePicker, WEEKDAYS, localToday, toggled } from "@/components/personalization/fields";
import { api, errorMessage } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import type { ExplanationStyle, UserProfile } from "@/types";

interface Form {
  exam_date: string;
  baseline_listening: string;
  baseline_reading: string;
  study_days: number[];
  new_cards_per_day: number;
  explanation_style: ExplanationStyle;
  focus_parts: string[];
  learning_goal_note: string;
  auto_adjust: boolean;
}

function toForm(profile: UserProfile): Form {
  return {
    exam_date: profile.exam_date ?? "",
    baseline_listening: profile.baseline_listening ? String(profile.baseline_listening) : "",
    baseline_reading: profile.baseline_reading ? String(profile.baseline_reading) : "",
    study_days: profile.study_days,
    new_cards_per_day: profile.effective_new_cards_per_day,
    explanation_style: profile.explanation_style,
    focus_parts: profile.focus_parts,
    learning_goal_note: profile.learning_goal_note ?? "",
    auto_adjust: profile.auto_adjust,
  };
}

export function PersonalizationCard({ profile, onSaved }: { profile: UserProfile; onSaved: (p: UserProfile) => void }) {
  const [form, setForm] = useState<Form>(() => toForm(profile));
  const [saving, setSaving] = useState(false);
  const [today] = useState(localToday);
  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((prev) => ({ ...prev, [key]: value }));

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.study_days.length) return;
    setSaving(true);
    try {
      const updated = await api<UserProfile>("/learner/profile", {
        method: "PATCH",
        json: {
          exam_date: form.exam_date || null,
          baseline_listening: form.baseline_listening ? Number(form.baseline_listening) : null,
          baseline_reading: form.baseline_reading ? Number(form.baseline_reading) : null,
          study_days: form.study_days,
          new_cards_per_day: form.new_cards_per_day,
          explanation_style: form.explanation_style,
          focus_parts: form.focus_parts,
          learning_goal_note: form.learning_goal_note.trim() || null,
          auto_adjust: form.auto_adjust,
        },
      });
      onSaved(updated);
      setForm(toForm(updated));
      toast.add({
        title: "Đã lưu cá nhân hoá",
        description: updated.days_to_exam != null ? `Còn ${updated.days_to_exam} ngày đến kỳ thi — lộ trình và kế hoạch 7 ngày đã cập nhật.` : "Kế hoạch 7 ngày đã được lập lại theo cài đặt mới.",
        type: "success",
      });
      void refreshLearner();
    } catch (err) {
      toast.add({ title: "Không lưu được", description: errorMessage(err), type: "error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card id="personalization" className="scroll-mt-20 border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
      <CardHeader className="border-b border-slate-100 pb-3 dark:border-slate-700/60">
        <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
          <SlidersHorizontal className="h-5 w-5 text-purple-500" aria-hidden="true" /> Cá nhân hoá lộ trình & AI
        </CardTitle>
        <p className="text-[11px] text-slate-500">Planner, mô hình kỹ năng và AI Mentor đọc trực tiếp các cài đặt này. AI cũng có thể đổi chúng khi bạn yêu cầu (có nhật ký + hoàn tác).</p>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={save} className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <Label htmlFor="pz-exam">Ngày thi</Label>
              <Input id="pz-exam" type="date" min={today} value={form.exam_date} onChange={(e) => set("exam_date", e.target.value)} />
              {profile.days_to_exam != null && <p className="text-[11px] text-slate-500">Còn {profile.days_to_exam} ngày</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="pz-l">Listening đầu vào</Label>
              <Input id="pz-l" type="number" min={5} max={495} step={5} value={form.baseline_listening} onChange={(e) => set("baseline_listening", e.target.value)} placeholder="5-495" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="pz-r">Reading đầu vào</Label>
              <Input id="pz-r" type="number" min={5} max={495} step={5} value={form.baseline_reading} onChange={(e) => set("baseline_reading", e.target.value)} placeholder="5-495" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Ngày học trong tuần</Label>
            <div className="flex flex-wrap gap-2">
              {WEEKDAYS.map((day, index) => (
                <Chip key={day} active={form.study_days.includes(index)} onClick={() => set("study_days", toggled(form.study_days, index))} label={`Học ${day}`}>{day}</Chip>
              ))}
            </div>
            {!form.study_days.length && <p className="text-[11px] text-red-500">Chọn ít nhất 1 ngày</p>}
          </div>

          <div className="space-y-1">
            <Label htmlFor="pz-cards">Thẻ từ vựng mới mỗi ngày: <strong>{form.new_cards_per_day}</strong></Label>
            <input id="pz-cards" type="range" min={0} max={40} value={form.new_cards_per_day} onChange={(e) => set("new_cards_per_day", Number(e.target.value))} className="w-full accent-blue-600" />
            <p className="text-[11px] text-slate-500">≈ {Math.ceil(form.new_cards_per_day * 0.75)} phút/ngày cho thẻ mới (+ ~12 giây mỗi thẻ ôn lại).</p>
          </div>

          <div className="space-y-1.5">
            <Label>Part ưu tiên</Label>
            <div className="flex flex-wrap gap-2">
              {PARTS.map((part) => (
                <Chip key={part} active={form.focus_parts.includes(part)} onClick={() => set("focus_parts", toggled(form.focus_parts, part))}>{part}</Chip>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>AI Mentor giải thích theo kiểu</Label>
            <StylePicker value={form.explanation_style} onChange={(value) => set("explanation_style", value)} />
          </div>

          <div className="space-y-1">
            <Label htmlFor="pz-goal">Mục tiêu & bối cảnh học (AI dùng để chọn ví dụ)</Label>
            <Textarea id="pz-goal" rows={2} maxLength={2000} value={form.learning_goal_note} onChange={(e) => set("learning_goal_note", e.target.value)} />
          </div>

          <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-700">
            <input type="checkbox" checked={form.auto_adjust} onChange={(e) => set("auto_adjust", e.target.checked)} className="mt-0.5 accent-blue-600" />
            <span>
              <strong className="text-slate-900 dark:text-white">Tự điều chỉnh kế hoạch</strong>
              <span className="block text-slate-500">Khi 7 ngày qua bạn hoàn thành dưới 50% nhiệm vụ, kế hoạch mới tạm nhẹ hơn 25% để bạn bắt nhịp lại. Không bao giờ tự tăng tải.</span>
            </span>
          </label>

          <Button type="submit" disabled={saving || !form.study_days.length} className="flex cursor-pointer items-center gap-1.5 bg-emerald-600 text-white hover:bg-emerald-500">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Check className="h-4 w-4" aria-hidden="true" />} Lưu & lập lại kế hoạch
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
