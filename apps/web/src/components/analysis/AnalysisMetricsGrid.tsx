import type { AnalysisResult } from "../../types/api";
import { RiskScoreBar } from "../analytics/RiskScoreBar";
import { StatCard } from "../patterns/StatCard";

export function AnalysisMetricsGrid({ analysis }: Readonly<{ analysis: AnalysisResult }>) {
  const maxScore = analysis.summary.max_risk_score;
  return (
    <section aria-label="Resumo da análise" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Heurísticas novas" value={String(analysis.summary.heuristic_threats_generated)} />
      <StatCard label="Já cobertas" value={String(analysis.summary.heuristic_threats_skipped_duplicate)} />
      <StatCard
        label="Maior L×I"
        value={maxScore == null ? "—" : String(maxScore)}
        footer={
          maxScore != null ? (
            <RiskScoreBar score={maxScore} caption="Maior L×I calculado nesta execução." />
          ) : null
        }
      />
      <StatCard label="Motor" value={analysis.engine_version} small />
      <StatCard label="Metodologia" value={analysis.methodology} small />
    </section>
  );
}
