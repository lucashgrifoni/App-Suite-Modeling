import { useMemo } from "react";
import type { AnalysisResult, HeuristicThreat } from "../../types/api";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";

function topN(threats: HeuristicThreat[], n: number): HeuristicThreat[] {
  const active = threats.filter((h) => !h.skipped_as_duplicate);
  return [...active].sort((a, b) => (b.risk.score ?? 0) - (a.risk.score ?? 0)).slice(0, n);
}

export function DecisionCockpit({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const pq = analysis.model_quality_precheck;
  const top = useMemo(() => topN(analysis.heuristic_threats, 3), [analysis.heuristic_threats]);
  const gaps = useMemo(() => {
    const checks = pq?.checks ?? [];
    return checks.filter((c) => !c.passed).slice(0, 3);
  }, [pq?.checks]);

  const recHigh =
    pq?.recommendation_confidence === "high" ||
    (pq?.methodology_fit_matrix.stride === "strong" && pq?.recommendation_confidence === "medium");

  return (
    <Card className="space-y-4 p-5" variant="elevated">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold text-otm-text">Cockpit de decisão</h2>
        <Badge tone={recHigh ? "ok" : "warn"}>
          Confiança: {pq?.recommendation_confidence ?? "—"}
        </Badge>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
            Top 3 prioridades (L×I)
          </p>
          <ol className="mt-2 list-decimal space-y-1.5 pl-4 text-sm text-otm-text-muted">
            {top.map((h) => (
              <li key={h.id}>
                <span className="font-medium text-otm-text">{h.title}</span>
                <span className="ml-1 text-xs text-otm-text-subtle">({h.stride})</span>
              </li>
            ))}
          </ol>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
            Lacunas do modelo (pré-check)
          </p>
          {gaps.length ? (
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
              {gaps.map((c) => (
                <li key={c.code}>{c.message}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-otm-text-muted">Sem lacunas críticas listadas pelo pré-check.</p>
          )}
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
            Sinais fortes
          </p>
          <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
            {analysis.wizard_context_notes && analysis.wizard_context_notes.length > 0 ? (
              analysis.wizard_context_notes.slice(0, 2).map((w) => <li key={w}>{w}</li>)
            ) : (
              <li>Sem sinais do assistente — preencha o questionário adaptativo para contextualizar.</li>
            )}
            {(analysis.anti_pattern_hits ?? []).length > 0 ? (
              <li>
                {(analysis.anti_pattern_hits ?? []).length} anti-padrão(ões) de modelagem relevantes ao template.
              </li>
            ) : null}
          </ul>
        </div>
      </div>
    </Card>
  );
}
