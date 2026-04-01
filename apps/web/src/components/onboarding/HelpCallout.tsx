import type { ReactNode } from "react";

type Tone = "info" | "tip";

export function HelpCallout({
  title,
  children,
  tone = "info",
  className = "",
}: Readonly<{
  title: string;
  children: ReactNode;
  tone?: Tone;
  className?: string;
}>) {
  const styles =
    tone === "tip"
      ? "border-otm-border-strong bg-otm-primary-muted"
      : "border-otm-border bg-otm-surface-2/90";
  return (
    <aside
      className={`rounded-otm-lg border px-4 py-3 text-sm leading-relaxed text-otm-text-muted ${styles} ${className}`}
    >
      <p className="font-display text-xs font-semibold uppercase tracking-wide text-otm-accent">{title}</p>
      <div className="mt-1.5">{children}</div>
    </aside>
  );
}
