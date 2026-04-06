import { useTranslation } from "react-i18next";
import { Card } from "../ui/Card";
import type { AnalysisResult } from "../../types/api";

export function Plot4aiContextCard({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const { t } = useTranslation();
  if (analysis.methodology !== "plot4ai" || !analysis.ai_system_context) return null;
  const ctx = analysis.ai_system_context;
  const patternTags = ctx.pattern_tags ?? [];
  const riskSurfaces = ctx.primary_risk_surfaces ?? [];
  const prioRecs = ctx.prioritized_recommendations ?? [];
  return (
    <Card title={t("plot4ai.cardTitle")} subtitle={t("plot4ai.subtitle")} variant="elevated">
      <p className="text-sm text-otm-text">{ctx.synopsis}</p>
      {patternTags.length > 0 ? (
        <p className="mt-2 text-xs text-otm-text-muted">
          <span className="font-medium text-otm-text">{t("plot4ai.patterns")}</span> {patternTags.join(", ")}
        </p>
      ) : null}
      {riskSurfaces.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-medium text-otm-text">{t("plot4ai.riskSurfaces")}</p>
          <ul className="mt-1 list-inside list-disc text-xs text-otm-text-muted">
            {riskSurfaces.slice(0, 4).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {prioRecs.length > 0 ? (
        <details className="mt-3 text-xs text-otm-text-muted">
          <summary className="cursor-pointer font-medium text-otm-text">{t("plot4ai.priorityActions")}</summary>
          <ul className="mt-1 list-inside list-disc">
            {prioRecs.slice(0, 5).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </Card>
  );
}
