"use client";

import { useMemo, useState } from "react";
import {
  BookOpen,
  Briefcase,
  Building2,
  CreditCard,
  FileText,
  HeartPulse,
  Laptop,
  Package,
  Plane,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Truck,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/states";
import { cn } from "@/lib/utils";
import type { CategoryStat } from "@/types";

const TOPIC_META: Record<string, { icon: typeof Briefcase; vi: string; color: string }> = {
  "General Business": { icon: Briefcase, vi: "Kinh doanh tổng quát & Thương mại", color: "text-blue-500 bg-blue-500/10 border-blue-500/20" },
  "Human Resources": { icon: Users, vi: "Nhân sự, Tuyển dụng & Đào tạo", color: "text-indigo-500 bg-indigo-500/10 border-indigo-500/20" },
  "Accounting & Finance": { icon: CreditCard, vi: "Kế toán, Ngân sách & Tài chính", color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" },
  "Computers & IT": { icon: Laptop, vi: "Công nghệ thông tin & Phần mềm", color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20" },
  "Marketing & Sales": { icon: Sparkles, vi: "Tiếp thị, Quảng cáo & Bán lẻ", color: "text-pink-500 bg-pink-500/10 border-pink-500/20" },
  "Office Operations": { icon: Building2, vi: "Vận hành công sở & Thủ tục hành chính", color: "text-amber-500 bg-amber-500/10 border-amber-500/20" },
  "Contracts & Agreements": { icon: FileText, vi: "Hợp đồng, Cam kết & Điều khoản", color: "text-purple-500 bg-purple-500/10 border-purple-500/20" },
  "Business Planning & Strategy": { icon: BookOpen, vi: "Chiến lược, Kế hoạch & Mục tiêu", color: "text-blue-600 bg-blue-600/10 border-blue-600/20" },
  "Banking & Finance": { icon: CreditCard, vi: "Ngân hàng, Giao dịch & Tín dụng", color: "text-teal-500 bg-teal-500/10 border-teal-500/20" },
  "Shipping & Logistics": { icon: Truck, vi: "Giao nhận, Kho vận & Chuỗi cung ứng", color: "text-orange-500 bg-orange-500/10 border-orange-500/20" },
  "Purchasing & Inventory": { icon: ShoppingBag, vi: "Mua sắm thiết bị & Quản lý kho", color: "text-rose-500 bg-rose-500/10 border-rose-500/20" },
  "Warranties & Consumer Rights": { icon: ShieldCheck, vi: "Bảo hành & Quyền lợi khách hàng", color: "text-emerald-600 bg-emerald-600/10 border-emerald-600/20" },
  "Manufacturing & Compliance": { icon: Package, vi: "Sản xuất, Nhà máy & Tiêu chuẩn QC", color: "text-yellow-600 bg-yellow-600/10 border-yellow-600/20" },
  "Conferences & Events": { icon: Users, vi: "Hội thảo, Sự kiện & Thuyết trình", color: "text-violet-500 bg-violet-500/10 border-violet-500/20" },
  "Travel & Hospitality": { icon: Plane, vi: "Du lịch, Lưu trú & Nhà hàng", color: "text-sky-500 bg-sky-500/10 border-sky-500/20" },
  "Health & Medical": { icon: HeartPulse, vi: "Y tế, Bảo hiểm & Sức khỏe", color: "text-red-500 bg-red-500/10 border-red-500/20" },
  "Real Estate & Leasing": { icon: Building2, vi: "Bất động sản & Thuê mặt bằng", color: "text-slate-500 bg-slate-500/10 border-slate-500/20" },
};

const DEFAULT_META = { icon: BookOpen, vi: "Chủ đề tiếng Anh doanh nghiệp", color: "text-slate-500 bg-slate-500/10 border-slate-500/20" };

interface TopicMatrixProps {
  stats: CategoryStat[];
  selectedCategory: string;
  onSelectTopic: (category: string, mode?: "srs" | "all") => void;
}

export function TopicMatrix({ stats, selectedCategory, onSelectTopic }: TopicMatrixProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return stats;
    return stats.filter((s) => {
      const meta = TOPIC_META[s.category] || DEFAULT_META;
      return s.category.toLowerCase().includes(q) || meta.vi.toLowerCase().includes(q);
    });
  }, [stats, query]);

  const totalWords = useMemo(() => stats.reduce((acc, s) => acc + s.total, 0), [stats]);
  const totalMastered = useMemo(() => stats.reduce((acc, s) => acc + s.mastered, 0), [stats]);
  const totalDue = useMemo(() => stats.reduce((acc, s) => acc + s.due, 0), [stats]);

  return (
    <div className="space-y-6">
      {/* Header filter & stats */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Danh Mục Chủ Đề Từ Vựng TOEIC ({stats.length} Chủ đề)
          </h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Chủ động chọn mảng nghiệp vụ bạn muốn tập trung ôn luyện hôm nay.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <Input
            aria-label="Tìm chủ đề"
            placeholder="Tìm theo tên chủ đề (VD: Hợp đồng, IT...)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 text-xs"
          />
        </div>
      </div>

      {/* Global Quick Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-xs dark:border-slate-800 dark:bg-slate-900/40">
        <div className="flex items-center gap-4 text-slate-600 dark:text-slate-400">
          <span>Tổng số: <strong className="text-slate-900 dark:text-white">{totalWords}</strong> từ</span>
          <span>•</span>
          <span>Cần ôn: <strong className="text-amber-600 dark:text-amber-400">{totalDue}</strong> thẻ</span>
          <span>•</span>
          <span>Đã thuộc: <strong className="text-emerald-600 dark:text-emerald-400">{totalMastered}</strong> thẻ</span>
        </div>

        <Button
          size="sm"
          variant={selectedCategory === "all" ? "default" : "outline"}
          onClick={() => onSelectTopic("all", "srs")}
          className="cursor-pointer text-xs"
        >
          <Play className="mr-1.5 h-3.5 w-3.5" /> Ôn tập tất cả chủ đề ({totalWords})
        </Button>
      </div>

      {/* Grid of Topics */}
      {filtered.length === 0 ? (
        <EmptyState title="Không tìm thấy chủ đề phù hợp" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item) => {
            const meta = TOPIC_META[item.category] || DEFAULT_META;
            const Icon = meta.icon;
            const percentMastered = item.total > 0 ? Math.round((item.mastered / item.total) * 100) : 0;
            const isSelected = selectedCategory === item.category;

            return (
              <div
                key={item.category}
                className={cn(
                  "group relative flex flex-col justify-between rounded-xl border bg-white p-4 transition-all duration-200 dark:bg-slate-900/60",
                  isSelected
                    ? "border-blue-500 shadow-md ring-1 ring-blue-500/30"
                    : "border-slate-200 hover:border-slate-300 hover:shadow-sm dark:border-slate-800 dark:hover:border-slate-700",
                )}
              >
                <div className="space-y-3">
                  {/* Top: Icon & Total count */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg border", meta.color)}>
                        <Icon className="h-5 w-5" aria-hidden="true" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                          {item.category}
                        </h3>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">{meta.vi}</p>
                      </div>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      {item.total} từ
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-500">
                      <span>Độ thành thục</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">{percentMastered}%</span>
                    </div>
                    <Progress value={percentMastered} className="h-1.5" />
                  </div>

                  {/* Breakdown badges */}
                  <div className="grid grid-cols-4 gap-1 pt-1 text-center text-[10px]">
                    <div className="rounded bg-slate-50 p-1 dark:bg-slate-800/40">
                      <div className="text-slate-400">Đến hạn</div>
                      <div className={cn("font-bold", item.due > 0 ? "text-amber-600 dark:text-amber-400" : "text-slate-600 dark:text-slate-400")}>
                        {item.due}
                      </div>
                    </div>
                    <div className="rounded bg-slate-50 p-1 dark:bg-slate-800/40">
                      <div className="text-slate-400">Từ mới</div>
                      <div className="font-bold text-blue-600 dark:text-blue-400">{item.new_cards}</div>
                    </div>
                    <div className="rounded bg-slate-50 p-1 dark:bg-slate-800/40">
                      <div className="text-slate-400">Đang học</div>
                      <div className="font-bold text-purple-600 dark:text-purple-400">{item.learning}</div>
                    </div>
                    <div className="rounded bg-slate-50 p-1 dark:bg-slate-800/40">
                      <div className="text-slate-400">Đã thuộc</div>
                      <div className="font-bold text-emerald-600 dark:text-emerald-400">{item.mastered}</div>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-4 flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/60">
                  <Button
                    size="sm"
                    variant="default"
                    onClick={() => onSelectTopic(item.category, "srs")}
                    className="flex-1 cursor-pointer text-xs"
                  >
                    <Play className="mr-1 h-3 w-3" /> Luyện SRS
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onSelectTopic(item.category, "all")}
                    className="cursor-pointer text-xs px-2.5"
                    title="Luyện tập toàn bộ từ vựng chủ đề này không giới hạn"
                  >
                    <RotateCcw className="mr-1 h-3 w-3" /> Ôn tăng cường
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
