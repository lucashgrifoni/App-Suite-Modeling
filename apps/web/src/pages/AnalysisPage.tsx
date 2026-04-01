import { useMemo, useState } from "react";
import { Navigate } from "react-router-dom";
import { analyzeDocument, fetchRemediationBacklog, recommendMethodology } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { EmptyState } from "../components/patterns/EmptyState";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { ContextHint } from "../components/onboarding/ContextHint";
import { RunEngineCard } from "../components/analysis/RunEngineCard";
import { AnalysisMetricsGrid } from "../components/analysis/AnalysisMetricsGrid";
import { Plot4aiContextCard } from "../components/analysis/Plot4aiContextCard";
import { ExplanationsSection } from "../components/analysis/ExplanationsSection";
import { RemediationBacklogCard } from "../components/analysis/RemediationBacklogCard";
import { MethodologyInsightsSection } from "../components/analysis/MethodologyInsightsSection";
import { ThreatsAnalysisCard } from "../components/analysis/ThreatsAnalysisCard";
import { useAnalysisHistory } from "../context/AnalysisHistoryContext";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { filterActiveThreats, listFrameworksFromAnalysisThreats } from "../utils/analysisFilters";
import type {
  HeuristicThreat,
  MethodologyRecommendation,
  RemediationBacklogResponse,
} from "../types/api";
import type { MethodologyId } from "../types/methodology";

export function AnalysisPage() {
  const { document, analysis, setAnalysis } = useSession();
  const { appendSnapshot } = useAnalysisHistory();
  const toast = useToast();
  const [packId, setPackId] = useState("");
  const [methodology, setMethodology] = useState<MethodologyId>(
    (document?.model?.methodology as MethodologyId) || "stride",
  );
  const [loading, setLoading] = useState(false);
  const [recommending, setRecommending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<MethodologyRecommendation | null>(null);
  const [minScore, setMinScore] = useState(0);
  const [frameworkFilter, setFrameworkFilter] = useState<string>("");
  const [explanationCategoryFilter, setExplanationCategoryFilter] = useState<string>("");
  const [backlog, setBacklog] = useState<RemediationBacklogResponse | null>(null);
  const [backlogLoading, setBacklogLoading] = useState(false);

  const doc = document;

  const frameworks = useMemo(() => {
    if (!analysis) return [];
    return listFrameworksFromAnalysisThreats(analysis.heuristic_threats);
  }, [analysis]);

  const filtered: HeuristicThreat[] = useMemo(() => {
    if (!analysis) return [];
    return filterActiveThreats(analysis.heuristic_threats, {
      minScore,
      frameworkFilter,
    });
  }, [analysis, minScore, frameworkFilter]);

  const explanationCategories = useMemo(() => {
    const values = (analysis?.explanations ?? []).map((e) => e.category).filter(Boolean);
    return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
  }, [analysis]);

  const visibleExplanations = useMemo(() => {
    const all = analysis?.explanations ?? [];
    if (!explanationCategoryFilter) return all;
    return all.filter((e) => e.category === explanationCategoryFilter);
  }, [analysis, explanationCategoryFilter]);

  const activeThreatCount = useMemo(() => {
    if (!analysis) return 0;
    return analysis.heuristic_threats.filter((h) => !h.skipped_as_duplicate).length;
  }, [analysis]);

  if (!doc) return <Navigate to="/" replace />;

  async function run() {
    if (!doc) return;
    setError(null);
    setLoading(true);
    try {
      const r = await analyzeDocument(doc, {
        packId: packId.trim() || null,
        methodology,
      });
      setAnalysis(r);
      appendSnapshot("analysis");
      toast.success("Análise gerada. Revise métricas e ameaças abaixo.");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Falha na análise.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  async function loadBacklog() {
    if (!doc || !analysis) return;
    setError(null);
    setBacklogLoading(true);
    try {
      const b = await fetchRemediationBacklog({ document: doc, analysis });
      setBacklog(b);
      toast.success("Backlog de remediação disponível.");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Falha ao gerar backlog.";
      setError(msg);
      toast.error(msg);
    } finally {
      setBacklogLoading(false);
    }
  }

  async function recommend() {
    if (!doc) return;
    setError(null);
    setRecommending(true);
    try {
      const rec = await recommendMethodology(doc);
      setRecommendation(rec);
      setMethodology(rec.methodology);
      toast.info(`Metodologia sugerida: ${rec.methodology}.`);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Falha ao recomendar metodologia.";
      setError(msg);
      toast.error(msg);
    } finally {
      setRecommending(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Motor de análise"
        title="Análise"
        description={
          <>
            Motor STRIDE, fronteiras de confiança e risco (L×I). Referências a frameworks vêm do
            servidor.
          </>
        }
      />

      <div className="space-y-2 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <ContextHint>
          O motor corre no servidor com o documento atual; depois pode <strong>exportar</strong> ou comparar versões no{" "}
          <strong>diff</strong>.
        </ContextHint>
      </div>

      <RunEngineCard
        methodology={methodology}
        onMethodologyChange={setMethodology}
        packId={packId}
        onPackIdChange={setPackId}
        loading={loading}
        recommending={recommending}
        recommendation={recommendation}
        onRun={() => void run()}
        onRecommend={() => void recommend()}
      />

      {error && <Alert>{error}</Alert>}

      {analysis && (
        <div className="space-y-8">
          <AnalysisMetricsGrid analysis={analysis} />
          <Plot4aiContextCard analysis={analysis} />
          {analysis.methodology_recommendation_reason && (
            <Alert variant="info">
              Recomendação aplicada: {analysis.methodology_recommendation_reason}
            </Alert>
          )}
          {analysis.explanations && analysis.explanations.length > 0 ? (
            <ExplanationsSection
              analysis={analysis}
              explanationCategoryFilter={explanationCategoryFilter}
              onExplanationCategoryChange={setExplanationCategoryFilter}
              visibleExplanations={visibleExplanations}
              explanationCategories={explanationCategories}
            />
          ) : null}
          <RemediationBacklogCard
            backlog={backlog}
            backlogLoading={backlogLoading}
            onLoad={() => void loadBacklog()}
          />
          <MethodologyInsightsSection analysis={analysis} />
          <ThreatsAnalysisCard
            filtered={filtered}
            activeThreatCount={activeThreatCount}
            minScore={minScore}
            onMinScoreChange={setMinScore}
            frameworkFilter={frameworkFilter}
            onFrameworkFilterChange={setFrameworkFilter}
            frameworks={frameworks}
          />
        </div>
      )}

      {analysis === null && (
        <EmptyState
          title="Motor ainda não executado"
          description={
            <>
              Confirme o modelo no assistente e no diagrama, escolha metodologia e use{" "}
              <strong className="text-otm-text">Gerar análise</strong> para obter heurísticas STRIDE, métricas L×I e
              referências a frameworks — tudo calculado no servidor.
            </>
          }
        />
      )}
    </div>
  );
}
