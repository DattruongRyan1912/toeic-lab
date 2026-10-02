import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { MobileBottomNav, MobileDrawer } from "@/components/layout/mobile-nav";
import { LearnerBootstrap } from "@/components/layout/learner-bootstrap";
import { AiCopilotWidget } from "@/components/ai-copilot-widget";
import { Toaster } from "@/components/ui/toast";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <Toaster>
      <div className="relative flex h-screen overflow-hidden bg-slate-100/80 font-sans text-slate-900 transition-colors duration-200 dark:bg-[#0f172a] dark:text-slate-100">
        <LearnerBootstrap />
        <Sidebar />
        <MobileDrawer />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto bg-slate-50/60 p-3.5 sm:p-5 md:p-8 transition-colors duration-200 dark:bg-[#0f172a]/60">
            <div className="mx-auto w-full max-w-[1520px] pb-24 md:pb-12">{children}</div>
          </main>
        </div>
        <MobileBottomNav />
        <AiCopilotWidget />
      </div>
    </Toaster>
  );
}
