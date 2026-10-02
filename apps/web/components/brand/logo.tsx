import Image from "next/image";
import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  size?: number;
  showText?: boolean;
  subtitle?: string;
  variant?: "mark" | "tile" | "full";
}

export function LogoMark({ className, size = 32 }: { className?: string; size?: number }) {
  return (
    <Image
      src="/logo-mark.png"
      alt="TOEIC Master"
      width={size}
      height={size}
      priority
      className={cn("object-contain drop-shadow-sm", className)}
    />
  );
}

export function LogoTile({ className, size = 32 }: { className?: string; size?: number }) {
  return (
    <div
      className={cn(
        "relative flex shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-700/60 bg-slate-900 shadow-md shadow-blue-950/40 transition-transform duration-200 group-hover:scale-105",
        className,
      )}
      style={{ width: size, height: size }}
    >
      <Image
        src="/logo-mark.png"
        alt="TOEIC Master"
        width={Math.round(size * 0.78)}
        height={Math.round(size * 0.78)}
        priority
        className="object-contain"
      />
    </div>
  );
}

export function BrandLogo({
  className,
  size = 32,
  showText = true,
  subtitle = "SELF-STUDY LAB",
  variant = "tile",
}: LogoProps) {
  return (
    <div className={cn("group flex items-center gap-3 select-none", className)}>
      {variant === "tile" ? (
        <LogoTile size={size} />
      ) : (
        <LogoMark size={size} />
      )}

      {showText && (
        <div className="flex flex-col">
          <span className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">
            TOEIC <span className="bg-gradient-to-r from-blue-600 to-indigo-500 bg-clip-text text-transparent dark:from-blue-400 dark:to-cyan-400">MASTER</span>
          </span>
          {subtitle && (
            <span className="font-mono text-[9.5px] font-bold tracking-wider text-blue-600 uppercase dark:text-cyan-400">
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
