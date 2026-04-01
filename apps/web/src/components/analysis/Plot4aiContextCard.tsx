import { Card } from "../ui/Card";
import type { AnalysisResult } from "../../types/api";

export function Plot4aiContextCard({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  if (analysis.methodology !== "plot4ai" || !analysis.ai_system_context) return null;
  const ctx = analysis.ai_system_context;
  return (
    <Card
      title="PLOT4ai — sistema com IA"
      subtitle="Deteção heurística a partir do modelo; não substitui revisão de arquitectura."
      variant="elevated"
    >
      <p className="text-sm text-otm-text">{ctx.synopsis}</p>
      {ctx.pattern_tags.length > 0 ? (
        <p className="mt-2 text-xs text-otm-text-muted">
          <span className="font-medium text-otm-text">Padrões:</span> {ctx.pattern_tags.join(", ")}
        </p>
      ) : null}
      {ctx.primary_risk_surfaces.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-medium text-otm-text">Superfícies de risco</p>
          <ul className="mt-1 list-inside list-disc text-xs text-otm-text-muted">
            {ctx.primary_risk_surfaces.slice(0, 4).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {ctx.prioritized_recommendations.length > 0 ? (
        <details className="mt-3 text-xs text-otm-text-muted">
          <summary className="cursor-pointer font-medium text-otm-text">Acções prioritárias (IA)</summary>
          <ul className="mt-1 list-inside list-disc">
            {ctx.prioritized_recommendations.slice(0, 5).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </Card>
  );
}
