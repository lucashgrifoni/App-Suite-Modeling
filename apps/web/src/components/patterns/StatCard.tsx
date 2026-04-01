import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  hint,
  small,
  footer,
  className = "",
}: Readonly<{
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  small?: boolean;
  footer?: ReactNode;
  className?: string;
}>) {
  return (
    <div
      className={`group relative overflow-hidden rounded-otm-md border border-otm-border bg-otm-surface-2/90 px-4 py-3 shadow-otm-sm transition duration-otm ease-otm hover:border-otm-border-strong hover:shadow-otm-glow ${className}`}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition group-hover:opacity-100"
        style={{
          background:
            "linear-gradient(135deg, rgba(86,255,149,0.06) 0%, transparent 55%)",
        }}
        aria-hidden
      />
      <p className="text-[11px] font-semibold uppercase tracking-wider text-otm-text-subtle">{label}</p>
      <p
        className={`relative mt-1 font-semibold text-otm-text ${small ? "text-sm" : "text-xl"}`}
      >
        {value}
      </p>
      {hint ? <p className="relative mt-1 text-xs text-otm-text-muted">{hint}</p> : null}
      {footer ? <div className="relative mt-3">{footer}</div> : null}
    </div>
  );
}
