import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  title,
  subtitle,
  variant = "default",
}: Readonly<{
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  variant?: "default" | "glass" | "elevated";
}>) {
  return (
    <section data-surface={variant} className={`work-panel ${className}`}>
      {title && (
        <header className="mb-4">
          <h2 className="font-display text-lg font-semibold text-otm-text">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-otm-text-muted">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
