import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  title,
  subtitle,
}: Readonly<{
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
}>) {
  return (
    <section
      className={`rounded-xl border border-[var(--asm-border)] bg-[var(--asm-surface)] p-5 shadow-sm ${className}`}
    >
      {title && (
        <header className="mb-4">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
