import { useTranslation } from "react-i18next";
import type { AnalysisResult } from "../../types/api";
import { Badge } from "../ui/Badge";

function completenessBadgeTone(s: string): "ok" | "warn" | "neutral" {
  if (s === "complete") return "ok";
  if (s === "partial") return "warn";
  return "neutral";
}

export function ModelQualityStrip({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const { t } = useTranslation();
  const pq = analysis.model_quality_precheck;
  const mc = analysis.methodology_completeness;
  const ap = analysis.anti_pattern_hits ?? [];
  const fitMatrix = pq?.methodology_fit_matrix ?? {};

  function bandLabel(band: string): string {
    if (band === "minimal") return t("modelQuality.bandMinimal");
    if (band === "good") return t("modelQuality.bandGood");
    if (band === "rich") return t("modelQuality.bandRich");
    return band;
  }

  function completenessLabel(s: string): string {
    if (s === "complete") return t("modelQuality.stateComplete");
    if (s === "partial") return t("modelQuality.statePartial");
    if (s === "degraded") return t("modelQuality.stateDegraded");
    return s;
  }

  if (!pq && !mc && ap.length === 0) return null;

  return (
    <section
      aria-label={t("modelQuality.aria")}
      data-testid="model-quality-strip"
      className="rounded-otm-lg border px-4 py-3 text-sm text-otm-text"
    >
      <div className="flex flex-wrap items-start gap-3">
        {pq ? (
          <div className="min-w-[200px] flex-1 space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
              {t("modelQuality.modelCompleteness")}
            </p>
            <p className="font-display text-xl font-semibold tabular-nums text-otm-text">{pq.score_0_100}</p>
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="neutral">{bandLabel(pq.band)}</Badge>
              <Badge tone="accent">{t("modelQuality.recConf", { conf: pq.recommendation_confidence })}</Badge>
            </div>
            <p className="text-xs text-otm-text-muted">
              {t("modelQuality.fitStride")}{" "}
              <span className="text-otm-text">{fitMatrix.stride ?? pq.methodology_fit}</span>
              {fitMatrix.pasta ? (
                <>
                  {" "}
                  {t("modelQuality.fitPasta")}{" "}
                  <span className="text-otm-text">{fitMatrix.pasta}</span>
                </>
              ) : null}
              {fitMatrix.nist_data_centric ? (
                <>
                  {" "}
                  {t("modelQuality.fitNist")}{" "}
                  <span className="text-otm-text">{fitMatrix.nist_data_centric}</span>
                </>
              ) : null}
            </p>
            {pq.checks?.length ? (
              <details className="mt-2 text-xs text-otm-text-muted">
                <summary className="cursor-pointer font-medium text-otm-text-subtle">
                  {t("modelQuality.precheckReasons", {
                    count: pq.checks.filter((c) => !c.passed).length,
                  })}
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
          <div className="min-w-[220px] flex-1 space-y-1 border-t pt-2 sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">
              {t("modelQuality.methodologyCompleteness")}
            </p>
            <Badge tone={completenessBadgeTone(mc.state)}>{completenessLabel(mc.state)}</Badge>
            {mc.note ? <p className="text-xs text-otm-text-muted">{mc.note}</p> : null}
            {(mc.reasons ?? []).length > 0 ? (
              <ul className="list-inside list-disc text-xs text-otm-text-muted">
                {(mc.reasons ?? []).slice(0, 4).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        {ap.length > 0 ? (
          <details className="min-w-[200px] flex-1 rounded-otm-md border border-amber-500/20 bg-amber-950/15 px-3 py-2">
            <summary className="cursor-pointer text-xs font-semibold text-amber-900 dark:text-amber-100">
              {t("modelQuality.antiPatterns", { count: ap.length })}
            </summary>
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
              {ap.slice(0, 5).map((h) => (
                <li key={h.id}>
                  <span className="text-otm-text">{h.name}</span>
                  {h.confidence_hint ? (
                    <span className="text-otm-text-subtle">
                      {t("modelQuality.confHint", { hint: h.confidence_hint })}
                    </span>
                  ) : null}
                  {" — "}
                  {h.message}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>
    </section>
  );
}
