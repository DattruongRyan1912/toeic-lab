"use client";

import React, { useState } from "react";
import { LogIn, UserPlus, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "@/components/ui/toast";

export function AuthModal() {
  const isOpen = useAuthStore((state) => state.isAuthModalOpen);
  const activeTab = useAuthStore((state) => state.authModalTab);
  const setOpen = useAuthStore((state) => state.setAuthModalOpen);
  const login = useAuthStore((state) => state.login);
  const register = useAuthStore((state) => state.register);

  // Form states
  const tab = activeTab;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Login inputs
  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register inputs
  const [regUsername, setRegUsername] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regDisplayName, setRegDisplayName] = useState("");
  const [regTargetScore, setRegTargetScore] = useState(800);

  const handleTabChange = (val: string) => {
    setOpen(true, val as "login" | "register");
    setError(null);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!loginIdentifier.trim() || !loginPassword) {
      setError("Vui lòng điền đầy đủ tên đăng nhập/email và mật khẩu");
      return;
    }

    try {
      setLoading(true);
      const user = await login(loginIdentifier, loginPassword);
      toast.add({
        title: "Đăng nhập thành công!",
        description: `Chào mừng trở lại, ${user.display_name || user.username}!`,
        type: "success",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!regUsername.trim() || !regEmail.trim() || !regPassword) {
      setError("Vui lòng điền đầy đủ các thông tin bắt buộc");
      return;
    }
    if (regPassword.length < 6) {
      setError("Mật khẩu phải có tối thiểu 6 ký tự");
      return;
    }

    try {
      setLoading(true);
      const user = await register({
        username: regUsername.trim(),
        email: regEmail.trim(),
        password: regPassword,
        display_name: regDisplayName.trim() || undefined,
        target_score: regTargetScore,
      });
      toast.add({
        title: "Tạo tài khoản thành công!",
        description: `Lộ trình TOEIC ${user.target_score}+ của bạn đã được kích hoạt.`,
        type: "success",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Đăng ký thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => setOpen(open, tab as "login" | "register")}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            {tab === "login" ? (
              <>
                <LogIn className="h-5 w-5 text-blue-600" />
                <span>Đăng nhập tài khoản</span>
              </>
            ) : (
              <>
                <UserPlus className="h-5 w-5 text-indigo-600" />
                <span>Đăng ký tài khoản học tập</span>
              </>
            )}
          </DialogTitle>
          <DialogDescription className="text-xs text-slate-500">
            Dữ liệu làm bài thi, nhật ký lỗi sai, chuỗi ngày học và thẻ SRS được lưu riêng biệt cho từng học viên.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-400 border border-red-200 dark:border-red-900/50">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <Tabs value={tab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-3">
            <TabsTrigger value="login" className="cursor-pointer">
              Đăng nhập
            </TabsTrigger>
            <TabsTrigger value="register" className="cursor-pointer">
              Đăng ký mới
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: LOGIN */}
          <TabsContent value="login">
            <form onSubmit={handleLogin} className="space-y-3.5">
              <div className="space-y-1.5">
                <Label htmlFor="login-id" className="text-xs font-semibold">Tên đăng nhập hoặc Email</Label>
                <Input
                  id="login-id"
                  type="text"
                  placeholder="ryan hoặc ryan@example.com"
                  value={loginIdentifier}
                  onChange={(e) => setLoginIdentifier(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="login-pw" className="text-xs font-semibold">Mật khẩu</Label>
                <Input
                  id="login-pw"
                  type="password"
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>

              <Button type="submit" disabled={loading} className="w-full cursor-pointer bg-blue-600 hover:bg-blue-500 text-white font-semibold">
                {loading ? "Đang xử lý..." : "Đăng nhập"}
              </Button>
            </form>
          </TabsContent>

          {/* TAB 2: REGISTER */}
          <TabsContent value="register">
            <form onSubmit={handleRegister} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label htmlFor="reg-user" className="text-xs font-semibold">Username *</Label>
                  <Input
                    id="reg-user"
                    type="text"
                    placeholder="ryan_dev"
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="reg-name" className="text-xs font-semibold">Tên hiển thị</Label>
                  <Input
                    id="reg-name"
                    type="text"
                    placeholder="Ryan Truong"
                    value={regDisplayName}
                    onChange={(e) => setRegDisplayName(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="reg-email" className="text-xs font-semibold">Email *</Label>
                <Input
                  id="reg-email"
                  type="email"
                  placeholder="name@company.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="reg-pw" className="text-xs font-semibold">Mật khẩu (tối thiểu 6 ký tự) *</Label>
                <Input
                  id="reg-pw"
                  type="password"
                  placeholder="••••••••"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5 pt-1">
                <Label className="text-xs font-semibold">Mục tiêu điểm số</Label>
                <div className="flex flex-wrap gap-1.5">
                  {[600, 750, 800, 850, 900].map((score) => (
                    <button
                      key={score}
                      type="button"
                      onClick={() => setRegTargetScore(score)}
                      className={`cursor-pointer rounded-full px-2.5 py-1 text-xs font-semibold transition-all ${
                        regTargetScore === score
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200"
                      }`}
                    >
                      {score}+
                    </button>
                  ))}
                </div>
              </div>

              <Button type="submit" disabled={loading} className="w-full mt-2 cursor-pointer bg-indigo-600 hover:bg-indigo-500 text-white font-semibold">
                {loading ? "Đang tạo tài khoản..." : "Tạo tài khoản học viên"}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
