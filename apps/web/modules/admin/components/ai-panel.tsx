"use client";

import { useState } from "react";
import { Activity, AlertTriangle, Coins, KeyRound, Power, PowerOff, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { ErrorState, LoadingState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { AdminAIKey, AdminAIOverview } from "@/types";

const ENDPOINT_LABELS: Record<string, string> = {
  chat: "AI Mentor",
  translate: "Dịch câu ví dụ",
  ai_fill: "Điền thẻ từ vựng",
  shadowing: "Chấm Shadowing",
  pronounce: "Chấm phát âm",
  voice_coach: "Voice Coach",
  system: "Hệ thống",
};

function Tile({ label, value, hint, icon: Icon }: { label: string; value: string | number; hint?: string; icon: typeof Activity }) {
  return (
    <Card className="border-slate-200 dark:border-slate-800">
      <CardContent className="flex items-start justify-between p-4">
        <div>
          <p className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase dark:text-slate-400">{label}</p>
          <p className="mt-1 text-2xl font-extrabold text-slate-900 tabular-nums dark:text-white">{value}</p>
          {hint && <p className="text-[11px] text-slate-500 dark:text-slate-400">{hint}</p>}
        </div>
        <Icon className="h-5 w-5 text-slate-400" aria-hidden="true" />
      </CardContent>
    </Card>
  );
}

function KeyRow({ item, busy, onToggle }: { item: AdminAIKey; busy: boolean; onToggle: (item: AdminAIKey) => void }) {
  const state = item.disabled ? "Đã tắt" : item.cooling_seconds ? `Tạm nghỉ ${item.cooling_seconds}s` : "Hoạt động";
  return (
    <tr className="align-top">
      <td className="py-2.5 pr-3">
        <p className="font-mono font-semibold text-slate-900 dark:text-white">{item.alias}</p>
        <p className="text-slate-500">{item.provider}</p>
      </td>
      <td className="py-2.5 pr-3">
        <span
          className={cn(
            "rounded px-1.5 py-0.5 text-[10px] font-semibold whitespace-nowrap",
            item.disabled
              ? "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              : item.cooling_seconds
                ? "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
                : "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300",
          )}
        >
          {state}
        </span>
        {item.note && <p className="mt-1 text-[10px] text-slate-500">{item.note}</p>}
      </td>
      <td className="py-2.5 pr-3 text-right tabular-nums">
        <span className="text-emerald-600 dark:text-emerald-400">{item.ok_24h}</span> /{" "}
        <span className="text-amber-600 dark:text-amber-400">{item.rate_limited_24h}</span> /{" "}
        <span className="text-red-600 dark:text-red-400">{item.errors_24h}</span>
      </td>
      <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-300">
        <p>OK: {formatDate(item.last_ok_at, true)}</p>
        {item.last_error_at && (
          <p className="text-red-600 dark:text-red-400" title={item.last_error ?? undefined}>
            Lỗi: {formatDate(item.last_error_at, true)} {item.last_error ? `— ${item.last_error.slice(0, 60)}` : ""}
          </p>
        )}
      </td>
      <td className="py-2.5 text-right">
        <Button size="xs" variant={item.disabled ? "outline" : "destructive"} disabled={busy} onClick={() => onToggle(item)} className="cursor-pointer">
          {item.disabled ? <Power aria-hidden="true" /> : <PowerOff aria-hidden="true" />}
          {item.disabled ? "Bật lại" : "Tắt key"}
        </Button>
      </td>
    </tr>
  );
}

/** Admin console tab: AI usage, key health and the default allowance (keys themselves stay in .env). */
export function AdminAIPanel() {
  const overview = useApi<AdminAIOverview>("/admin/ai?days=7");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  if (overview.error && !overview.data) return <ErrorState message={overview.error} onRetry={overview.reload} />;
  if (!overview.data) return <LoadingState label="Đang tải thống kê AI..." />;
  const data = overview.data;
  const maxRequests = Math.max(1, ...data.days.map((d) => d.requests));

  const toggle = async (item: AdminAIKey) => {
    const disabling = !item.disabled;
    const note = disabling ? window.prompt(`Tắt key ${item.alias}? Ghi chú lý do (tuỳ chọn):`, "") : "";
    if (note === null) return;
    setBusyKey(item.alias);
    try {
      const next = await api<AdminAIOverview>(`/admin/ai/keys/${encodeURIComponent(item.alias)}`, {
        method: "PATCH",
        json: { disabled: disabling, note: note || null },
      });
      overview.mutate(() => next);
      toast.add({ title: disabling ? "Đã tắt key" : "Đã bật lại key", description: item.alias, type: "success" });
    } catch (err) {
      toast.add({ title: "Không cập nhật được key", description: errorMessage(err), type: "error" });
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label="Lượt AI hôm nay" value={data.today.requests} hint={`${data.today.calls} lần gọi provider`} icon={Sparkles} />
        <Tile label="Token hôm nay" value={data.today.tokens.toLocaleString("vi-VN")} icon={Coins} />
        <Tile label="Lỗi hôm nay" value={data.today.errors} hint="gồm cả 429 đã tự chuyển key" icon={AlertTriangle} />
        <Tile
          label="Provider đang dùng"
          value={data.provider.offline ? "Offline" : data.provider.provider}
          hint={data.provider.offline ? "trả lời từ database" : (data.provider.model ?? undefined)}
          icon={Activity}
        />
      </div>

      <Card className="border-slate-200 dark:border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4 text-purple-500" aria-hidden="true" /> Key API (24 giờ qua)
          </CardTitle>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Key thật chỉ nằm trong <code>.env</code> trên server; ở đây chỉ bật/tắt theo alias. Key bị 429/403 tự nghỉ {data.limits.key_cooldown_seconds}s và được thử sau cùng.
          </p>
        </CardHeader>
        <CardContent>
          {data.keys.length === 0 ? (
            <p className="text-xs text-slate-500">Chưa cấu hình key nào: AI đang chạy chế độ offline.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-xs">
                <thead className="border-b border-slate-200 text-[10px] tracking-wider text-slate-500 uppercase dark:border-slate-800">
                  <tr>
                    <th className="py-2 pr-3 font-semibold">Key</th>
                    <th className="py-2 pr-3 font-semibold">Trạng thái</th>
                    <th className="py-2 pr-3 text-right font-semibold">OK / 429 / Lỗi</th>
                    <th className="py-2 pr-3 font-semibold">Gần nhất</th>
                    <th className="py-2 text-right font-semibold">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {data.keys.map((item) => (
                    <KeyRow key={item.alias} item={item} busy={busyKey === item.alias} onToggle={(k) => void toggle(k)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader>
            <CardTitle className="text-base">Lượt AI 7 ngày</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5 text-xs">
            {data.days.map((day) => (
              <div key={day.date} className="flex items-center gap-2">
                <span className="w-12 shrink-0 text-slate-500">{formatDate(day.date)}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900">
                  <div className="h-2 rounded-full bg-purple-500" style={{ width: `${(day.requests / maxRequests) * 100}%` }} />
                </div>
                <span className="w-28 shrink-0 text-right tabular-nums text-slate-600 dark:text-slate-300">
                  {day.requests} lượt • {day.tokens.toLocaleString("vi-VN")} tk
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader>
            <CardTitle className="text-base">Dùng nhiều nhất (7 ngày)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {data.top_users.length === 0 ? (
              <p className="text-slate-500">Chưa có lượt dùng AI nào.</p>
            ) : (
              <ul className="space-y-1">
                {data.top_users.map((row) => (
                  <li key={row.user_id} className="flex justify-between">
                    <span className="font-mono">@{row.username}</span>
                    <span className="tabular-nums text-slate-600 dark:text-slate-300">
                      {row.requests} lượt • {row.tokens.toLocaleString("vi-VN")} tk
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {data.by_endpoint.length > 0 && (
              <div className="border-t border-slate-100 pt-2 dark:border-slate-800">
                <p className="mb-1 font-semibold text-slate-700 dark:text-slate-200">Theo chức năng</p>
                {data.by_endpoint.map((row) => (
                  <p key={row.endpoint} className="flex justify-between">
                    <span>{ENDPOINT_LABELS[row.endpoint] ?? row.endpoint}</span>
                    <span className="tabular-nums">{row.requests}</span>
                  </p>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-[11px] text-slate-500 dark:text-slate-400">
        Hạn mức mặc định: {data.limits.daily_quota} lượt/ngày cho học viên (kèm giới hạn ngắn {data.limits.burst}), {data.limits.guest_daily_quota} lượt/ngày cho khách.
        Admin và tài khoản được cấp &ldquo;không giới hạn&rdquo; không bị áp hạn mức; tài khoản có hạn mức riêng dùng số đó thay cho mặc định.
        Đổi mặc định bằng <code>AI_DAILY_QUOTA</code> / <code>AI_GUEST_DAILY_QUOTA</code> trong <code>.env</code>. Nhật ký giữ {data.limits.retention_days} ngày.
      </p>
    </div>
  );
}
