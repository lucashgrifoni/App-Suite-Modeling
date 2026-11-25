import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  className = "",
}: Readonly<{
  title: string;
  description?: ReactNode;
  eyebrow?: string;
  actions?: ReactNode;
  className?: string;
}>) {
  return (
    <header
      className={`flex flex-col gap-4 pb-1 sm:flex-row sm:items-end sm:justify-between ${className}`}
    >
      <div className="max-w-3xl space-y-2">
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[color:var(--otm-primary-ink)]">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="font-display text-[32px] font-semibold leading-tight tracking-tight text-otm-text md:text-[42px]">
          {title}
        </h1>
        {description ? (
          <div className="text-[15px] leading-relaxed text-otm-text-muted">{description}</div>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}
