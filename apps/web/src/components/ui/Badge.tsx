import type { ReactNode } from "react";

type BadgeProps = {
  children: ReactNode;
  tone?: "neutral" | "warn" | "ok" | "accent";
};

export function Badge({ children, tone = "neutral" }: Readonly<BadgeProps>) {
  const tones = {
    neutral: "border border-otm-border bg-otm-surface-3 text-otm-text-muted",
    warn: "border border-amber-500/30 bg-amber-500/10 text-amber-100",
    ok: "border border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
    accent: "border border-otm-border-strong bg-otm-primary-subtle text-otm-accent",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
