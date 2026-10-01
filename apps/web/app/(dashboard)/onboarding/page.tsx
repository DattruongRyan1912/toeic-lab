"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, CalendarDays, Check, GraduationCap, Loader2, Sparkles, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { Chip, PARTS, StylePicker, WEEKDAYS, localToday, toggled } from "@/components/personalization/fields";
import { api, errorMessage } from "@/lib/api";
import { refreshLearner } from "@/lib/learner-store";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { ExplanationStyle, PlanWeek, UserProfile } from "@/types";

const LEVELS = [
  { label: "Mới bắt đầu", listening: 150, reading: 120 },
  { label: "~450", listening: 250, reading: 200 },
  { label: "~600", listening: 320, reading: 280 },
  { label: "~750", listening: 390, reading: 360 },
  { label: "Tự nhập", listening: null, reading: null },
];

interface FormState {
  display_name: string;
  headline: string;
  target_score: number;
  exam_date: string;
  baseline_listening: string;
  baseline_reading: string;
  daily_goal_minutes: number;
  study_days: number[];
  new_cards_per_day: number;
  explanation_style: ExplanationStyle;
  focus_parts: string[];
  weak_areas: string;
  learning_goal_note: string;
}

function initialForm(profile: UserProfile): FormState {
  return {
    display_name: profile.display_name ?? "",
    headline: profile.headline ?? "",
    target_score: profile.target_score,
    exam_date: profile.exam_date ?? "",
    baseline_listening: profile.baseline_listening ? String(profile.baseline_listening) : "",
    baseline_reading: profile.baseline_reading ? String(profile.baseline_reading) : "",
    daily_goal_minutes: profile.daily_goal_minutes,
    study_days: profile.study_days,
    new_cards_per_day: profile.effective_new_cards_per_day,
    explanation_style: profile.explanation_style,
    focus_parts: profile.focus_parts,
    weak_areas: "",
    learning_goal_note: profile.learning_goal_note ?? "",
  };
}

function Wizard({ profile }: { profile: UserProfile }) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>(() => initialForm(profile));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((prev) => ({ ...prev, [key]: value }));
  const toggleDay = (day: number) => setForm((prev) => ({ ...prev, study_days: toggled(prev.study_days, day) }));
  const togglePart = (part: string) => setForm((prev) => ({ ...prev, focus_parts: toggled(prev.focus_parts, part) }));

  const [today] = useState(localToday);
  const weeksLeft = form.exam_date ? Math.ceil((Date.parse(form.exam_date) - Date.parse(today)) / (7 * 86400000)) : null;
  const steps = ["Mục tiêu", "Trình độ", "Lịch học"];

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const result = await api<{ profile: UserProfile; plan: PlanWeek }>("/learner/onboarding", {
        method: "POST",
        json: {
          display_name: form.display_name || null,
          headline: form.headline || null,
          target_score: form.target_score,
          exam_date: form.exam_date || null,
          baseline_listening: form.baseline_listening ? Number(form.baseline_listening) : null,
          baseline_reading: form.baseline_reading ? Number(form.baseline_reading) : null,
          daily_goal_minutes: form.daily_goal_minutes,
          study_days: form.study_days,
          new_cards_per_day: form.new_cards_per_day,
          explanation_style: form.explanation_style,
          focus_parts: form.focus_parts,
          weak_areas: form.weak_areas || null,
          learning_goal_note: form.learning_goal_note || null,
        },
      });
      const today = result.plan.days[0];
      toast.add({
        title: "Đã tạo lộ trình cá nhân hoá",
        description: `${today.items.length} nhiệm vụ hôm nay (~${today.planned_minutes} phút)${result.profile.days_to_exam != null ? ` • còn ${result.profile.days_to_exam} ngày đến kỳ thi` : ""}`,
        type: "success",
      });
      await refreshLearner();
      router.push("/");
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  const canNext = step !== 2 || form.study_days.length > 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="text-center">
        <Sparkles className="mx-auto h-8 w-8 text-blue-500" aria-hidden="true" />
        <h1 className="mt-2 text-2xl font-extrabold text-slate-900 dark:text-white">Cá nhân hoá lộ trình TOEIC của bạn</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">3 bước, khoảng 2 phút. Bạn có thể đổi lại mọi thứ trong Cài đặt hoặc nhờ AI Mentor.</p>
      </div>

      <ol className="flex items-center justify-center gap-2" aria-label="Các bước">
        {steps.map((label, index) => (
          <li key={label} className="flex items-center gap-2">
            <span
              aria-current={index === step ? "step" : undefined}
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold",
                index < step ? "bg-emerald-500 text-white" : index === step ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
              )}
            >
              {index < step ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : index + 1}
            </span>
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{label}</span>
            {index < steps.length - 1 && <span className="h-px w-8 bg-slate-300 dark:bg-slate-600" />}
          </li>
        ))}
      </ol>

      <Card className="border-slate-200 bg-white dark:border-slate-700/70 dark:bg-slate-800/80">
        {step === 0 && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><Target className="h-5 w-5 text-blue-500" aria-hidden="true" /> Mục tiêu & ngày thi</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label htmlFor="ob-name">Tên của bạn</Label>
                  <Input id="ob-name" value={form.display_name} onChange={(e) => set("display_name", e.target.value)} placeholder="Ryan" />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="ob-headline">Công việc</Label>
                  <Input id="ob-headline" value={form.headline} onChange={(e) => set("headline", e.target.value)} placeholder="Backend Engineer" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Điểm mục tiêu</Label>
                <div className="flex flex-wrap gap-2">
                  {[600, 700, 750, 800, 850, 900].map((score) => (
                    <Chip key={score} active={form.target_score === score} onClick={() => set("target_score", score)}>{score}+</Chip>
                  ))}
                  <Input aria-label="Điểm mục tiêu khác" type="number" min={10} max={990} step={5} value={form.target_score}
                    onChange={(e) => set("target_score", Number(e.target.value))} className="h-8 w-24" />
                </div>
              </div>
              <div className="space-y-1">
                <Label htmlFor="ob-exam">Ngày thi dự kiến (không bắt buộc)</Label>
                <Input id="ob-exam" type="date" min={today} value={form.exam_date} onChange={(e) => set("exam_date", e.target.value)} className="w-48" />
                <p className="text-[11px] text-slate-500">
                  {weeksLeft != null && weeksLeft > 0
                    ? `Còn khoảng ${weeksLeft} tuần — các mốc của lộ trình 24 tuần sẽ được nén/giãn cho vừa, 2 tuần cuối tăng thi thử bấm giờ.`
                    : "Có ngày thi, lộ trình sẽ tự co giãn và kế hoạch tăng thi thử khi gần ngày thi."}
                </p>
              </div>
              <div className="space-y-1">
                <Label htmlFor="ob-goal">Vì sao bạn cần TOEIC? (AI dùng để chọn ví dụ phù hợp)</Label>
                <Textarea id="ob-goal" rows={2} value={form.learning_goal_note} onChange={(e) => set("learning_goal_note", e.target.value)}
                  placeholder="VD: Cần 800 để apply công ty outsource Nhật, đọc tài liệu kỹ thuật tốt nhưng nghe yếu" />
              </div>
            </CardContent>
          </>
        )}

        {step === 1 && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><GraduationCap className="h-5 w-5 text-emerald-500" aria-hidden="true" /> Trình độ hiện tại</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label>Điểm gần nhất (hoặc ước lượng)</Label>
                <div className="flex flex-wrap gap-2">
                  {LEVELS.map((level) => (
                    <Chip
                      key={level.label}
                      active={level.listening !== null && form.baseline_listening === String(level.listening) && form.baseline_reading === String(level.reading)}
                      onClick={() => {
                        if (level.listening !== null) {
                          set("baseline_listening", String(level.listening));
                          set("baseline_reading", String(level.reading));
                        }
                      }}
                    >
                      {level.label}
                    </Chip>
                  ))}
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label htmlFor="ob-l">Listening (5-495)</Label>
                  <Input id="ob-l" type="number" min={5} max={495} step={5} value={form.baseline_listening} onChange={(e) => set("baseline_listening", e.target.value)} placeholder="VD: 300" />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="ob-r">Reading (5-495)</Label>
                  <Input id="ob-r" type="number" min={5} max={495} step={5} value={form.baseline_reading} onChange={(e) => set("baseline_reading", e.target.value)} placeholder="VD: 280" />
                </div>
              </div>
              <p className="text-[11px] text-slate-500">Điểm đầu vào là điểm xuất phát của mô hình kỹ năng; sau vài bài luyện, dữ liệu thật của bạn sẽ thay thế dần.</p>
              <div className="space-y-1.5">
                <Label>Part muốn ưu tiên</Label>
                <div className="flex flex-wrap gap-2">
                  {PARTS.map((part) => (
                    <Chip key={part} active={form.focus_parts.includes(part)} onClick={() => togglePart(part)}>{part}</Chip>
                  ))}
                </div>
              </div>
              <div className="space-y-1">
                <Label htmlFor="ob-weak">Bạn hay sai dạng nào? (AI sẽ ghi nhớ)</Label>
                <Textarea id="ob-weak" rows={2} value={form.weak_areas} onChange={(e) => set("weak_areas", e.target.value)}
                  placeholder="VD: Hay nhầm liên từ/giới từ, nghe giọng Anh-Úc kém, Part 7 hết giờ" />
              </div>
            </CardContent>
          </>
        )}

        {step === 2 && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><CalendarDays className="h-5 w-5 text-purple-500" aria-hidden="true" /> Lịch học & cách học</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label>Mỗi ngày học được bao lâu?</Label>
                <div className="flex flex-wrap gap-2">
                  {[20, 30, 45, 60, 90].map((minutes) => (
                    <Chip key={minutes} active={form.daily_goal_minutes === minutes} onClick={() => set("daily_goal_minutes", minutes)}>{minutes} phút</Chip>
                  ))}
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Ngày học trong tuần</Label>
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.map((day, index) => (
                    <Chip key={day} active={form.study_days.includes(index)} onClick={() => toggleDay(index)} label={`Học ${day}`}>{day}</Chip>
                  ))}
                </div>
                {form.study_days.length === 0 && <p className="text-[11px] text-red-500">Chọn ít nhất 1 ngày</p>}
              </div>
              <div className="space-y-1">
                <Label htmlFor="ob-cards">Thẻ từ vựng mới mỗi ngày: <strong>{form.new_cards_per_day}</strong></Label>
                <input id="ob-cards" type="range" min={0} max={40} step={1} value={form.new_cards_per_day}
                  onChange={(e) => set("new_cards_per_day", Number(e.target.value))} className="w-full accent-blue-600" />
                <p className="text-[11px] text-slate-500">≈ {Math.ceil(form.new_cards_per_day * 0.75)} phút/ngày cho thẻ mới, cộng ~12 giây cho mỗi thẻ đến hạn ôn. Hệ thống sẽ gợi ý giảm nếu tỉ lệ nhớ thấp.</p>
              </div>
              <div className="space-y-1.5">
                <Label>AI Mentor giải thích theo kiểu</Label>
                <StylePicker value={form.explanation_style} onChange={(value) => set("explanation_style", value)} />
              </div>
            </CardContent>
          </>
        )}
      </Card>

      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">{error}</p>}

      <div className="flex justify-between">
        <Button variant="outline" disabled={step === 0 || saving} onClick={() => setStep((s) => s - 1)} className="cursor-pointer">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Quay lại
        </Button>
        {step < 2 ? (
          <Button disabled={!canNext} onClick={() => setStep((s) => s + 1)} className="cursor-pointer bg-blue-600 text-white hover:bg-blue-500">
            Tiếp tục <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        ) : (
          <Button disabled={saving || !canNext} onClick={() => void submit()} className="cursor-pointer bg-emerald-600 text-white hover:bg-emerald-500">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Sparkles className="h-4 w-4" aria-hidden="true" />}
            Tạo lộ trình của tôi
          </Button>
        )}
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  const profile = useApi<UserProfile>("/learner/profile");
  if (profile.error) return <ErrorState message={profile.error} onRetry={profile.reload} />;
  if (!profile.data) return <LoadingState label="Đang tải hồ sơ..." />;
  return <Wizard profile={profile.data} />;
}
