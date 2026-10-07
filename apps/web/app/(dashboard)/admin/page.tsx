"use client";

import { useEffect, useState } from "react";
import { Activity, ChevronLeft, ChevronRight, Lock, LockOpen, LogIn, Search, ShieldCheck, ShieldOff, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { api, errorMessage } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { formatDate, percent } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { AdminRole, AdminUserDetail, AdminUserList, AdminUserRow } from "@/types";

const PAGE_SIZE = 50;
const SELECT = "rounded-lg border border-input bg-transparent p-2 text-xs text-slate-800 dark:bg-input/30 dark:text-slate-200";

function RoleBadge({ role }: { role: string }) {
  const admin = role === "admin";
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold whitespace-nowrap",
        admin ? "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
      )}
    >
      {role}
    </span>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-semibold whitespace-nowrap",
        active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300" : "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300",
      )}
    >
      {active ? "Hoạt động" : "Đã khoá"}
    </span>
  );
}

function StatTile({ label, value, icon: Icon }: { label: string; value: number | string; icon: typeof Users }) {
  return (
    <Card className="border-slate-200 dark:border-slate-800">
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase dark:text-slate-400">{label}</p>
          <p className="mt-1 text-2xl font-extrabold text-slate-900 tabular-nums dark:text-white">{value}</p>
        </div>
        <Icon className="h-5 w-5 text-slate-400" aria-hidden="true" />
      </CardContent>
    </Card>
  );
}

function UserDetailDialog({ userId, onClose }: { userId: number | null; onClose: () => void }) {
  const detail = useApi<AdminUserDetail>(userId === null ? null : `/admin/users/${userId}`);
  const user = detail.data?.id === userId ? detail.data : undefined;
  return (
    <Dialog open={userId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{user ? user.display_name : "Chi tiết người dùng"}</DialogTitle>
        </DialogHeader>
        {detail.error && !user ? (
          <ErrorState message={detail.error} onRetry={detail.reload} />
        ) : !user ? (
          <LoadingState />
        ) : (
          <div className="space-y-4 text-xs">
            <div className="flex flex-wrap items-center gap-2 text-slate-600 dark:text-slate-300">
              <span className="font-mono">@{user.username}</span>
              <span>{user.email ?? "—"}</span>
              <RoleBadge role={user.role} />
              <StatusBadge active={user.is_active} />
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
              {[
                ["Mục tiêu", user.target_score],
                ["Ngày thi", formatDate(user.exam_date)],
                ["Onboarding", user.onboarded ? "Đã xong" : "Chưa"],
                ["Tham gia", formatDate(user.created_at)],
                ["Hoạt động cuối", formatDate(user.last_active_at, true)],
                ["Phút học 7 ngày", user.study_minutes_7d],
                ["Tổng phút học", user.study_minutes_total],
                ["Câu đã làm", user.attempts],
                ["Độ chính xác", percent(user.accuracy)],
                ["Bài nộp", user.submissions],
                ["Lượt ôn SRS", user.srs_reviews],
                ["Lỗi chưa xử lý", user.open_errors],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <dt className="text-[10px] text-slate-500 uppercase dark:text-slate-400">{label}</dt>
                  <dd className="font-semibold text-slate-900 tabular-nums dark:text-white">{value}</dd>
                </div>
              ))}
            </dl>
            <div>
              <p className="mb-1.5 font-semibold text-slate-700 dark:text-slate-200">Bài nộp gần nhất</p>
              {user.recent_submissions.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Chưa có bài nộp.</p>
              ) : (
                <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
                  {user.recent_submissions.map((s) => (
                    <li key={s.id} className="flex items-center justify-between px-3 py-2">
                      <span>
                        <span className="font-mono">{s.test_id}</span> · {s.part ?? "—"} · {s.mode ?? "—"}
                      </span>
                      <span className="tabular-nums text-slate-600 dark:text-slate-300">
                        {s.correct_count ?? 0}/{s.total_questions ?? 0} · {formatDate(s.submitted_at, true)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function AdminPage() {
  const authUser = useAuthStore((state) => state.user);
  const authLoading = useAuthStore((state) => state.loading);
  const openLogin = useAuthStore((state) => state.openLogin);

  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<"" | AdminRole>("");
  const [status, setStatus] = useState<"" | "active" | "locked">("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  // Debounce the search box so typing does not fire one request per key.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(search.trim());
      setOffset(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const isAdmin = authUser?.role === "admin";
  const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
  if (query) params.set("q", query);
  if (role) params.set("role", role);
  if (status) params.set("status", status);
  const list = useApi<AdminUserList>(isAdmin ? `/admin/users?${params}` : null);

  async function update(user: AdminUserRow, change: { role?: AdminRole; is_active?: boolean }, confirmText: string) {
    if (!window.confirm(confirmText)) return;
    setBusyId(user.id);
    try {
      await api<AdminUserDetail>(`/admin/users/${user.id}`, { method: "PATCH", json: change });
      toast.add({ title: "Đã cập nhật", description: `@${user.username}`, type: "success" });
      list.reload();
    } catch (err) {
      toast.add({ title: "Không cập nhật được", description: errorMessage(err), type: "error" });
    } finally {
      setBusyId(null);
    }
  }

  const header = (
    <div>
      <span className="text-[11px] font-semibold tracking-wider text-violet-600 uppercase dark:text-violet-400">Admin Console</span>
      <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-white">Quản Trị Hệ Thống</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Quản lý tài khoản học viên: khoá/mở khoá, phân quyền và xem tiến độ học.</p>
    </div>
  );

  if (authLoading) return <LoadingState />;
  if (!isAdmin) {
    return (
      <div className="space-y-6">
        {header}
        <Card className="border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <Lock className="h-8 w-8 text-slate-400" aria-hidden="true" />
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {authUser ? "Tài khoản của bạn không có quyền quản trị." : "Vui lòng đăng nhập bằng tài khoản quản trị."}
            </p>
            {!authUser && (
              <Button onClick={openLogin} className="cursor-pointer text-xs">
                <LogIn className="h-3.5 w-3.5" aria-hidden="true" /> Đăng nhập
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const data = list.data;
  return (
    <div className="space-y-6">
      {header}

      {data && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Tổng tài khoản" value={data.summary.total_users} icon={Users} />
          <StatTile label="Hoạt động 7 ngày" value={data.summary.active_7d} icon={Activity} />
          <StatTile label="Quản trị viên" value={data.summary.admins} icon={ShieldCheck} />
          <StatTile label="Đã khoá" value={data.summary.locked} icon={Lock} />
        </div>
      )}

      <Card className="border-slate-200 dark:border-slate-800">
        <CardHeader className="gap-3">
          <CardTitle className="text-base">Người dùng {data ? `(${data.total})` : ""}</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-56 flex-1">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm username, email, tên hiển thị..." className="pl-8 text-xs" aria-label="Tìm người dùng" />
            </div>
            <select className={SELECT} value={role} onChange={(e) => { setRole(e.target.value as "" | AdminRole); setOffset(0); }} aria-label="Lọc theo quyền">
              <option value="">Mọi quyền</option>
              <option value="learner">Learner</option>
              <option value="admin">Admin</option>
            </select>
            <select className={SELECT} value={status} onChange={(e) => { setStatus(e.target.value as "" | "active" | "locked"); setOffset(0); }} aria-label="Lọc theo trạng thái">
              <option value="">Mọi trạng thái</option>
              <option value="active">Hoạt động</option>
              <option value="locked">Đã khoá</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {list.error && !data ? (
            <ErrorState message={list.error} onRetry={list.reload} />
          ) : !data ? (
            <LoadingState />
          ) : data.items.length === 0 ? (
            <EmptyState title="Không có người dùng phù hợp" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-xs">
                <thead className="border-b border-slate-200 text-[10px] tracking-wider text-slate-500 uppercase dark:border-slate-800 dark:text-slate-400">
                  <tr>
                    <th className="py-2 pr-3 font-semibold">Người dùng</th>
                    <th className="py-2 pr-3 font-semibold">Quyền</th>
                    <th className="py-2 pr-3 font-semibold">Trạng thái</th>
                    <th className="py-2 pr-3 font-semibold">Hoạt động cuối</th>
                    <th className="py-2 pr-3 text-right font-semibold">Phút 7 ngày</th>
                    <th className="py-2 pr-3 text-right font-semibold">Câu / Đúng</th>
                    <th className="py-2 text-right font-semibold">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {data.items.map((user) => {
                    const self = user.id === authUser?.id;
                    const busy = busyId === user.id;
                    return (
                      <tr key={user.id} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40" onClick={() => setSelected(user.id)}>
                        <td className="py-2.5 pr-3">
                          <p className="font-semibold text-slate-900 dark:text-white">
                            {user.display_name} {self && <span className="text-[10px] font-normal text-slate-400">(bạn)</span>}
                          </p>
                          <p className="text-slate-500 dark:text-slate-400">
                            @{user.username} · {user.email ?? "chưa có email"}
                            {!user.has_password && " · không đăng nhập được"}
                          </p>
                        </td>
                        <td className="py-2.5 pr-3"><RoleBadge role={user.role} /></td>
                        <td className="py-2.5 pr-3"><StatusBadge active={user.is_active} /></td>
                        <td className="py-2.5 pr-3 text-slate-600 dark:text-slate-300">{formatDate(user.last_active_at, true)}</td>
                        <td className="py-2.5 pr-3 text-right tabular-nums">{user.study_minutes_7d}</td>
                        <td className="py-2.5 pr-3 text-right tabular-nums">
                          {user.attempts} / {percent(user.accuracy)}
                        </td>
                        <td className="py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex justify-end gap-1.5">
                            <Button
                              size="xs"
                              variant="outline"
                              disabled={self || busy}
                              className="cursor-pointer"
                              onClick={() =>
                                update(
                                  user,
                                  { role: user.role === "admin" ? "learner" : "admin" },
                                  user.role === "admin" ? `Thu hồi quyền admin của @${user.username}?` : `Cấp quyền admin cho @${user.username}?`,
                                )
                              }
                            >
                              {user.role === "admin" ? <ShieldOff aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />}
                              {user.role === "admin" ? "Thu hồi admin" : "Cấp admin"}
                            </Button>
                            <Button
                              size="xs"
                              variant={user.is_active ? "destructive" : "outline"}
                              disabled={self || busy}
                              className="cursor-pointer"
                              onClick={() =>
                                update(
                                  user,
                                  { is_active: !user.is_active },
                                  user.is_active ? `Khoá @${user.username}? Phiên đăng nhập hiện tại sẽ bị vô hiệu ngay.` : `Mở khoá @${user.username}?`,
                                )
                              }
                            >
                              {user.is_active ? <Lock aria-hidden="true" /> : <LockOpen aria-hidden="true" />}
                              {user.is_active ? "Khoá" : "Mở khoá"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {data && data.total > PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-end gap-2 text-xs text-slate-500">
              <span>
                {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} / {data.total}
              </span>
              <Button size="icon-sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} aria-label="Trang trước" className="cursor-pointer">
                <ChevronLeft aria-hidden="true" />
              </Button>
              <Button size="icon-sm" variant="outline" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)} aria-label="Trang sau" className="cursor-pointer">
                <ChevronRight aria-hidden="true" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <UserDetailDialog userId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
