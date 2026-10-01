"use client";

import Link from "next/link";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const components: Components = {
  h1: ({ children }) => <h2 className="mt-4 mb-2 text-lg font-bold text-slate-900 dark:text-slate-100">{children}</h2>,
  h2: ({ children }) => <h3 className="mt-4 mb-2 text-base font-bold text-slate-900 dark:text-slate-100">{children}</h3>,
  h3: ({ children }) => <h4 className="mt-3 mb-1.5 text-sm font-bold text-slate-900 dark:text-slate-100">{children}</h4>,
  h4: ({ children }) => <h5 className="mt-3 mb-1 text-sm font-semibold text-slate-800 dark:text-slate-200">{children}</h5>,
  p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="my-1.5 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-1.5 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  hr: () => <hr className="my-3 border-slate-200 dark:border-slate-700" />,
  blockquote: ({ children }) => (
    <blockquote className="my-2 rounded-r-lg border-l-4 border-blue-400 bg-blue-50/70 px-3 py-1.5 text-slate-700 dark:border-blue-500/60 dark:bg-blue-500/10 dark:text-slate-300">
      {children}
    </blockquote>
  ),
  code: ({ children, className }) => (
    <code
      className={cn(
        "rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] text-purple-700 dark:bg-slate-900/80 dark:text-purple-300",
        className,
      )}
    >
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-slate-100 p-3 text-xs dark:bg-slate-900/80 [&>code]:bg-transparent [&>code]:p-0">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full border-collapse text-left text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-100 dark:bg-slate-900/70">{children}</thead>,
  th: ({ children }) => <th className="border-b border-slate-200 px-2.5 py-1.5 font-semibold dark:border-slate-700">{children}</th>,
  td: ({ children }) => <td className="border-b border-slate-100 px-2.5 py-1.5 align-top dark:border-slate-800">{children}</td>,
  a: ({ href, children }) => {
    if (href?.startsWith("/")) {
      return (
        <Link href={href} className="font-medium text-blue-600 underline underline-offset-2 dark:text-blue-400">
          {children}
        </Link>
      );
    }
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-600 underline underline-offset-2 dark:text-blue-400">
        {children}
      </a>
    );
  },
};

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("text-sm text-slate-700 dark:text-slate-300 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
