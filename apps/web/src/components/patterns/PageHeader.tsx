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
      className={`flex flex-col gap-4 border-b border-otm-border pb-8 sm:flex-row sm:items-end sm:justify-between ${className}`}
    >
      <div className="max-w-3xl space-y-2">
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-otm-mint-400/90">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="font-display text-3xl font-semibold tracking-tight text-otm-text md:text-4xl">
          {title}
        </h1>
        {description ? (
          <div className="text-base leading-relaxed text-otm-text-muted md:text-lg">{description}</div>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}
