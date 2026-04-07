import type { ReactNode } from "react";

type BadgeProps = {
  children: ReactNode;
  tone?: "neutral" | "warn" | "ok" | "accent";
};

export function Badge({ children, tone = "neutral" }: Readonly<BadgeProps>) {
  const tones = {
    neutral: "border border-otm-border bg-otm-surface-3 text-otm-text-muted",
    warn:
      "border border-amber-600/30 bg-amber-500/15 text-amber-950 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100",
    ok:
      "border border-emerald-600/30 bg-emerald-500/12 text-emerald-950 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100",
    accent:
      "border border-otm-border-strong bg-otm-primary-subtle text-emerald-900 dark:text-otm-accent",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
