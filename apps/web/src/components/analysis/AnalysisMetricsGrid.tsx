import { useTranslation } from "react-i18next";
import type { AnalysisResult } from "../../types/api";
import { WorkspaceStat } from "../patterns/ModelSummary";

export function AnalysisMetricsGrid({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const { t } = useTranslation();
  const maxScore = analysis.summary.max_risk_score;
  return (
    <section aria-label={t("metrics.aria")}>
      <div className="work-stats">
        <WorkspaceStat
          icon="target"
          label={t("metrics.newHeuristics")}
          value={analysis.summary.heuristic_threats_generated}
          hint={analysis.methodology}
        />
        <WorkspaceStat
          icon="flag"
          label={t("metrics.maxLi")}
          value={maxScore ?? "—"}
          hint={t("work.riskFormula")}
        />
        <WorkspaceStat
          icon="boundary"
          label={t("work.crossings")}
          value={analysis.trust_boundary_findings.filter((f) => f.code === "CROSS_BOUNDARY_FLOW").length}
        />
        <WorkspaceStat
          icon="list"
          label={t("work.quality")}
          value={
            analysis.model_quality_precheck ? `${analysis.model_quality_precheck.score_0_100}/100` : "—"
          }
        />
      </div>
      <p className="mt-2 text-xs text-otm-text-muted">
        {t("metrics.engine")} {analysis.engine_version} · {t("metrics.alreadyCovered")}{" "}
        {analysis.summary.heuristic_threats_skipped_duplicate ?? 0}
      </p>
    </section>
  );
}
