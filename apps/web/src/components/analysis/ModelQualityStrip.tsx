import type { AnalysisResult } from "../../types/api";
import { Badge } from "../ui/Badge";

function bandLabel(band: string): string {
  if (band === "minimal") return "Mínimo";
  if (band === "good") return "Bom";
  if (band === "rich") return "Rico";
  return band;
}

function completenessLabel(s: string): string {
  if (s === "complete") return "Completa";
  if (s === "partial") return "Parcial";
  if (s === "degraded") return "Degradada";
  return s;
}

function completenessBadgeTone(s: string): "ok" | "warn" | "neutral" {
  if (s === "complete") return "ok";
  if (s === "partial") return "warn";
  return "neutral";
}

export function ModelQualityStrip({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const pq = analysis.model_quality_precheck;
  const mc = analysis.methodology_completeness;
  const ap = analysis.anti_pattern_hits ?? [];

  if (!pq && !mc && ap.length === 0) return null;

  return (
    <section
      aria-label="Qualidade do modelo e metodologia"
      className="rounded-otm-lg border border-otm-border/90 bg-otm-surface-1/60 px-4 py-3 text-sm text-otm-text"
    >
      <div className="flex flex-wrap items-start gap-3">
        {pq ? (
          <div className="min-w-[200px] flex-1 space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
              Model completeness
            </p>
            <p className="font-display text-xl font-semibold tabular-nums text-otm-text">{pq.score_0_100}</p>
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="neutral">{bandLabel(pq.band)}</Badge>
              <Badge tone="accent">Conf. recomendações: {pq.recommendation_confidence}</Badge>
            </div>
            <p className="text-xs text-otm-text-muted">
              Fit STRIDE:{" "}
              <span className="text-otm-text">{pq.methodology_fit_matrix.stride ?? pq.methodology_fit}</span>
              {pq.methodology_fit_matrix.pasta ? (
                <>
                  {" "}
                  · PASTA:{" "}
                  <span className="text-otm-text">{pq.methodology_fit_matrix.pasta}</span>
                </>
              ) : null}
              {pq.methodology_fit_matrix.nist_data_centric ? (
                <>
                  {" "}
                  · NIST DC:{" "}
                  <span className="text-otm-text">{pq.methodology_fit_matrix.nist_data_centric}</span>
                </>
              ) : null}
            </p>
            {pq.checks?.length ? (
              <details className="mt-2 text-xs text-otm-text-muted">
                <summary className="cursor-pointer font-medium text-otm-text-subtle">
                  Razões do pré-check ({pq.checks.filter((c) => !c.passed).length} em falta)
                </summary>
                <ul className="mt-1 list-inside list-disc space-y-0.5">
                  {pq.checks
                    .filter((c) => !c.passed)
                    .slice(0, 5)
                    .map((c) => (
                      <li key={c.code}>{c.message}</li>
                    ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : null}
        {mc ? (
          <div className="min-w-[220px] flex-1 space-y-1 border-t border-otm-border/60 pt-2 sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
              Methodology completeness
            </p>
            <Badge tone={completenessBadgeTone(mc.state)}>
              {completenessLabel(mc.state)}
            </Badge>
            {mc.note ? <p className="text-xs text-otm-text-muted">{mc.note}</p> : null}
            {mc.reasons.length > 0 ? (
              <ul className="list-inside list-disc text-xs text-otm-text-muted">
                {mc.reasons.slice(0, 4).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        {ap.length > 0 ? (
          <details className="min-w-[200px] flex-1 rounded-otm-md border border-amber-500/20 bg-amber-950/15 px-3 py-2">
            <summary className="cursor-pointer text-xs font-semibold text-amber-100">
              Anti-padrões ({ap.length})
            </summary>
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
              {ap.slice(0, 5).map((h) => (
                <li key={h.id}>
                  <span className="text-otm-text">{h.name}</span> — {h.message}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>
    </section>
  );
}
