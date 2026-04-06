import { useMemo } from "react";
import { Link } from "react-router-dom";
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
    <div data-testid="decision-cockpit">
      <Card className="space-y-4 p-5" variant="elevated">
        <div
          className="rounded-otm-md border border-otm-border/60 bg-otm-surface-2/35 px-3 py-3"
          data-testid="cockpit-executive-strip"
        >
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
            Leitura executiva
          </p>
          <p className="mt-1 text-sm leading-relaxed text-otm-text-muted">
            {pq ? (
              <>
                Modelo na banda <strong className="text-otm-text">{pq.band}</strong> (pré-check{" "}
                {pq.score_0_100}/100). Confiança nas recomendações:{" "}
                <strong className="text-otm-text">{pq.recommendation_confidence}</strong>.
              </>
            ) : (
              <>Corra o motor para obter pré-check, prioridades e lacunas com contexto.</>
            )}{" "}
            {top[0] ? (
              <>
                Pico de risco heurístico: <strong className="text-otm-text">{top[0].title}</strong>.
              </>
            ) : null}
          </p>
          <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-otm-text-muted">
            <Link className="font-medium text-otm-accent hover:underline" to="/diff">
              Comparar versões
            </Link>
            <span className="text-otm-text-subtle">·</span>
            <Link className="font-medium text-otm-accent hover:underline" to="/export">
              Exportar artefactos
            </Link>
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-sm font-semibold text-otm-text">Cockpit de decisão</h2>
          <Badge tone={recHigh ? "ok" : "warn"}>
            Confiança: {pq?.recommendation_confidence ?? "—"}
          </Badge>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
        <div data-testid="cockpit-priorities">
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
        <div data-testid="cockpit-gaps">
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
        <div data-testid="cockpit-wizard-signals">
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
          {analysis.wizard_signal_trace && analysis.wizard_signal_trace.length > 0 ? (
            <details
              data-testid="cockpit-guided-trace"
              className="mt-3 rounded-otm-md border border-otm-border/70 bg-otm-surface-2/40 px-2 py-2"
            >
              <summary className="cursor-pointer text-[11px] font-semibold text-otm-text-subtle">
                Rastreio da modelação guiada (audit trail)
              </summary>
              <ul className="mt-2 list-inside list-disc space-y-1.5 text-[11px] text-otm-text-muted">
                {analysis.wizard_signal_trace.slice(0, 8).map((e) => (
                  <li key={`${e.source_tag}-${e.effect}`}>
                    <span className="font-medium text-otm-text">{e.effect}</span> · {e.weight} ·{" "}
                    {e.mechanism}
                    <br />
                    <span className="text-otm-text-subtle">{e.explanation}</span>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
        </div>
      </Card>
    </div>
  );
}
