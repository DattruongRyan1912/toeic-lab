import { AlertTriangle, Inbox, Loader2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LoadingState({ label = "Đang tải dữ liệu..." }: { label?: string }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-2 p-10 text-sm text-slate-500 dark:text-slate-400">
      <Loader2 className="h-6 w-6 animate-spin text-blue-500" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
      <AlertTriangle className="h-5 w-5" aria-hidden="true" />
      <p>{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="cursor-pointer">
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Thử lại
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
      <Inbox className="h-6 w-6 text-slate-400" aria-hidden="true" />
      <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p>
      {children && <div className="max-w-md text-xs text-slate-500 dark:text-slate-400">{children}</div>}
    </div>
  );
}
