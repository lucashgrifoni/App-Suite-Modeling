import type { ReactNode } from "react";

/**
 * Dica contextual discreta (linha única ou bloco curto).
 */
export function ContextHint({
  children,
  className = "",
}: Readonly<{ children: ReactNode; className?: string }>) {
  return (
    <p
      className={`text-xs leading-relaxed text-otm-text-subtle [&_strong]:font-medium [&_strong]:text-otm-text-muted ${className}`}
    >
      {children}
    </p>
  );
}
