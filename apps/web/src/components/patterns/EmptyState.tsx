import type { ReactNode } from "react";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
}: Readonly<{
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}>) {
  return (
    <div
      className={`relative overflow-hidden rounded-otm-xl border border-dashed border-otm-border-strong bg-otm-primary-muted px-6 py-12 text-center ${className}`}
    >
      <div
        className="pointer-events-none absolute -left-24 top-0 h-48 w-48 rounded-full blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-16 bottom-0 h-40 w-40 rounded-full blur-3xl"
        aria-hidden
      />
      <div className="relative mx-auto flex max-w-md flex-col items-center gap-3">
        {icon ? (
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-otm-border bg-otm-surface-2 shadow-otm-sm">
            {icon}
          </div>
        ) : null}
        <h3 className="font-display text-lg font-semibold text-otm-text">{title}</h3>
        {description ? <p className="text-sm leading-relaxed text-otm-text-muted">{description}</p> : null}
        {action ? <div className="mt-2">{action}</div> : null}
      </div>
    </div>
  );
}
