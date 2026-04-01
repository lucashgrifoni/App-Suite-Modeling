import type { ReactNode } from "react";

export function SectionHeader({
  title,
  subtitle,
  actions,
  className = "",
}: Readonly<{
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string;
}>) {
  return (
    <div
      className={`mb-4 flex flex-col gap-2 sm:mb-5 sm:flex-row sm:items-center sm:justify-between ${className}`}
    >
      <div>
        <h2 className="font-display text-lg font-semibold text-otm-text">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-otm-text-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
