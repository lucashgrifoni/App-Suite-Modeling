import type { ReactNode } from "react";

/**
 * Entrada suave de conteúdo; combine com key no pai para animar troca de rota.
 */
export function FadeIn({
  children,
  className = "",
}: Readonly<{ children: ReactNode; className?: string }>) {
  return (
    <div className={`motion-reduce:animate-none animate-page-enter ${className}`}>{children}</div>
  );
}
