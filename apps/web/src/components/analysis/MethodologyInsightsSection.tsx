import { Card } from "../ui/Card";
import type { AnalysisResult } from "../../types/api";

export function MethodologyInsightsSection({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const blocks = analysis.methodology_insights?.blocks;
  if (!blocks?.length) return null;
  return (
    <Card
      title="Insights da metodologia"
      subtitle={
        analysis.methodology_insights?.profile ?? "Complementos específicos da metodologia escolhida."
      }
      variant="elevated"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {blocks.slice(0, 6).map((b) => (
          <div
            key={b.key}
            className="rounded-otm-md border border-otm-border bg-otm-surface-1 p-3 otm-tilt-hover"
          >
            <p className="text-sm font-semibold text-otm-text">{b.title}</p>
            <ul className="mt-2 space-y-1 text-xs text-otm-text-muted">
              {(b.items ?? []).slice(0, 3).map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}
