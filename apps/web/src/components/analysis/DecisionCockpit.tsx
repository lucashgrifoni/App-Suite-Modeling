import { useMemo } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { AnalysisResult, HeuristicThreat } from "../../types/api";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";

function topN(threats: HeuristicThreat[], n: number): HeuristicThreat[] {
  const active = threats.filter((h) => !h.skipped_as_duplicate);
  return [...active].sort((a, b) => (b.risk.score ?? 0) - (a.risk.score ?? 0)).slice(0, n);
}

export function DecisionCockpit({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const { t } = useTranslation();
  const pq = analysis.model_quality_precheck;
  const top = useMemo(() => topN(analysis.heuristic_threats, 3), [analysis.heuristic_threats]);
  const gaps = useMemo(() => {
    const checks = pq?.checks ?? [];
    return checks.filter((c) => !c.passed).slice(0, 3);
  }, [pq?.checks]);

  const strideFit = pq?.methodology_fit_matrix?.stride;
  const recHigh =
    pq?.recommendation_confidence === "high" ||
    (strideFit === "strong" && pq?.recommendation_confidence === "medium");

  return (
    <div data-testid="decision-cockpit">
      <Card className="space-y-4 p-5" variant="elevated">
        <div
          className="rounded-otm-md border px-3 py-3"
          data-testid="cockpit-executive-strip"
        >
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
            {t("decisionCockpit.executiveRead")}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-otm-text-muted">
            {pq ? (
              <Trans
                i18nKey="decisionCockpit.bandLine"
                values={{
                  band: pq.band,
                  score: pq.score_0_100,
                  conf: pq.recommendation_confidence,
                }}
                components={{
                  0: <strong className="text-otm-text" />,
                  1: <strong className="text-otm-text" />,
                  2: <strong className="text-otm-text" />,
                  3: <strong className="text-otm-text" />,
                }}
              />
            ) : (
              t("decisionCockpit.runEngineHint")
            )}{" "}
            {top[0] ? (
              <Trans
                i18nKey="decisionCockpit.riskPeak"
                values={{ title: top[0].title }}
                components={{ 0: <strong className="text-otm-text" /> }}
              />
            ) : null}
          </p>
          <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-otm-text-muted">
            <Link className="font-medium text-otm-accent hover:underline" to="/diff">
              {t("decisionCockpit.compareVersions")}
            </Link>
            <span className="text-otm-text-subtle">·</span>
            <Link className="font-medium text-otm-accent hover:underline" to="/export">
              {t("decisionCockpit.exportArtifacts")}
            </Link>
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-sm font-semibold text-otm-text">{t("decisionCockpit.title")}</h2>
          <Badge tone={recHigh ? "ok" : "warn"}>
            {t("decisionCockpit.confidence")} {pq?.recommendation_confidence ?? "—"}
          </Badge>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <div data-testid="cockpit-priorities">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
              {t("decisionCockpit.top3")}
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
              {t("decisionCockpit.modelGaps")}
            </p>
            {gaps.length ? (
              <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
                {gaps.map((c) => (
                  <li key={c.code}>{c.message}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-otm-text-muted">{t("decisionCockpit.noGaps")}</p>
            )}
          </div>
          <div data-testid="cockpit-wizard-signals">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
              {t("decisionCockpit.strongSignals")}
            </p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
              {analysis.wizard_context_notes && analysis.wizard_context_notes.length > 0 ? (
                analysis.wizard_context_notes.slice(0, 2).map((w) => <li key={w}>{w}</li>)
              ) : (
                <li>{t("decisionCockpit.noWizardSignals")}</li>
              )}
              {(analysis.anti_pattern_hits ?? []).length > 0 ? (
                <li>
                  {t("decisionCockpit.antiPatternHits", {
                    count: (analysis.anti_pattern_hits ?? []).length,
                  })}
                </li>
              ) : null}
            </ul>
            {analysis.wizard_signal_trace && analysis.wizard_signal_trace.length > 0 ? (
              <details
                data-testid="cockpit-guided-trace"
                className="mt-3 rounded-otm-md border px-2 py-2"
              >
                <summary className="cursor-pointer text-[11px] font-semibold text-otm-text-subtle">
                  {t("decisionCockpit.auditTrail")}
                </summary>
                <ul className="mt-2 list-inside list-disc space-y-1.5 text-[11px] text-otm-text-muted">
                  {analysis.wizard_signal_trace.slice(0, 8).map((e) => (
                    <li key={`${e.source_tag}-${e.effect}`}>
                      <span className="font-medium text-otm-text">{e.effect}</span> · {e.weight} · {e.mechanism}
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
