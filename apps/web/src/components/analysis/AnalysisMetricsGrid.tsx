import { useTranslation } from "react-i18next";
import type { AnalysisResult } from "../../types/api";
import { RiskScoreBar } from "../analytics/RiskScoreBar";
import { StatCard } from "../patterns/StatCard";

export function AnalysisMetricsGrid({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const { t } = useTranslation();
  const maxScore = analysis.summary.max_risk_score;
  return (
    <section aria-label={t("metrics.aria")} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label={t("metrics.newHeuristics")} value={String(analysis.summary.heuristic_threats_generated)} />
      <StatCard label={t("metrics.alreadyCovered")} value={String(analysis.summary.heuristic_threats_skipped_duplicate)} />
      <StatCard
        label={t("metrics.maxLi")}
        value={maxScore == null ? "—" : String(maxScore)}
        footer={
          maxScore != null ? (
            <RiskScoreBar score={maxScore} caption={t("metrics.riskCaption")} />
          ) : null
        }
      />
      <StatCard label={t("metrics.engine")} value={analysis.engine_version} small />
      <StatCard label={t("metrics.methodology")} value={analysis.methodology} small />
    </section>
  );
}
