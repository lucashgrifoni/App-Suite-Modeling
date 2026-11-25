import type { ReactNode } from "react";

/**
 * Os tons carregam tinta explícita para claro *e* escuro (mesmo padrão do Badge).
 * Antes só existia a variante escura (text-*-200), que perdia contraste sobre as
 * superfícies claras. As tintas -950 sobre o fundo a 12% dão 11.2–12.5:1.
 * As bordas são decorativas: o estado é lido pelo texto, não pela cor (WCAG 1.4.1).
 */
const TONES = {
  neutral: "border-otm-border bg-otm-surface-3 text-otm-text-muted",
  success:
    "border-emerald-600/30 bg-emerald-500/12 text-emerald-950 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
  warning:
    "border-amber-600/30 bg-amber-500/12 text-amber-950 dark:border-amber-500/35 dark:bg-amber-500/10 dark:text-amber-200",
  danger:
    "border-red-600/30 bg-red-500/12 text-red-950 dark:border-red-500/35 dark:bg-red-500/10 dark:text-red-200",
  info: "border-sky-600/30 bg-sky-500/12 text-sky-950 dark:border-sky-500/35 dark:bg-sky-500/10 dark:text-sky-200",
} as const;

export function StatusPill({
  tone = "neutral",
  children,
  className = "",
}: Readonly<{
  tone?: keyof typeof TONES;
  children: ReactNode;
  className?: string;
}>) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
