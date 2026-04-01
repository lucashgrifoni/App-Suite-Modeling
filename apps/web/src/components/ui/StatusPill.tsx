import type { ReactNode } from "react";

export function StatusPill({
  tone = "neutral",
  children,
  className = "",
}: Readonly<{
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  children: ReactNode;
  className?: string;
}>) {
  const tones = {
    neutral: "border-otm-border bg-otm-surface-3 text-otm-text-muted",
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    warning: "border-amber-500/35 bg-amber-500/10 text-amber-200",
    danger: "border-red-500/35 bg-red-500/10 text-red-200",
    info: "border-sky-500/35 bg-sky-500/10 text-sky-200",
  } as const;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
