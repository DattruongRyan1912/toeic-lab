"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

const subscribe = () => () => {};

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // true only on the client, avoids a hydration mismatch without setState-in-effect
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);

  if (!mounted) {
    return <div className="h-8 w-8 sm:w-28 rounded-full bg-slate-200/60 dark:bg-slate-800/40 shrink-0" aria-hidden="true" />;
  }

  const isDark = resolvedTheme === "dark";
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="flex h-8 w-8 sm:w-auto p-0 sm:px-3 cursor-pointer items-center justify-center sm:gap-1.5 rounded-full border-slate-300 bg-white/80 text-xs font-semibold text-slate-800 shadow-xs transition-all hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-100 dark:hover:bg-slate-700/80 shrink-0"
      aria-label={isDark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
    >
      {isDark ? (
        <>
          <Sun className="h-3.5 w-3.5 fill-amber-500/20 text-amber-500" aria-hidden="true" />
          <span className="hidden text-[11px] font-medium sm:inline">Chế Độ Sáng</span>
        </>
      ) : (
        <>
          <Moon className="h-3.5 w-3.5 fill-blue-600/20 text-blue-600" aria-hidden="true" />
          <span className="hidden text-[11px] font-medium sm:inline">Tối Êm Dịu</span>
        </>
      )}
    </Button>
  );
}
