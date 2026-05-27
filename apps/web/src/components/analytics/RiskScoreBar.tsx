import { useTranslation } from "react-i18next";

/**
 * Barra de risco L×I (0–maxScore) sem dependências — útil para demos e leitura rápida.
 */
export function RiskScoreBar({
  score,
  maxScore = 25,
  variant = "default",
  caption,
  className = "",
}: Readonly<{
  score: number | null | undefined;
  maxScore?: number;
  /** default: legenda curta; compact: só a barra; none: sem legenda */
  variant?: "default" | "compact" | "none";
  caption?: string | null;
  className?: string;
}>) {
  const { t } = useTranslation();
  const s = score ?? 0;
  const pct = Math.min(100, Math.max(0, (s / maxScore) * 100));
  const label =
    score == null
      ? t("riskBar.noScore")
      : t("riskBar.liAria", { score: s, max: maxScore });
  let footer: string | null;
  if (caption === undefined) {
    footer = variant === "default" ? t("riskBar.scaleFooter") : null;
  } else {
    footer = caption;
  }
  const showFooter =
    footer != null && String(footer).length > 0 && variant !== "compact" && variant !== "none";

  return (
    <div className={className}>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-otm-surface-3"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={maxScore}
        aria-valuenow={s}
        aria-label={label}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-otm-primary via-otm-mint-400 to-amber-500/90 motion-reduce:transition-none transition-[width] duration-otm ease-otm"
          style={{ width: `${pct}%` }}
        />
      </div>
      {showFooter ? <p className="mt-1 text-[10px] text-otm-text-subtle">{footer}</p> : null}
    </div>
  );
}
