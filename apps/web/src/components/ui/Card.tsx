import type { ReactNode } from "react";

const variants = {
  default: "border border-otm-border bg-otm-surface-2/90 shadow-otm-sm",
  glass: "otm-glass border-otm-border shadow-otm-md",
  elevated:
    "border border-otm-border-strong bg-otm-surface-2 shadow-otm-lg otm-perspective otm-card-lift",
};

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
  variant?: keyof typeof variants;
}>) {
  return (
    <section
      className={`rounded-otm-xl p-5 md:p-6 ${variants[variant]} ${className}`}
    >
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
