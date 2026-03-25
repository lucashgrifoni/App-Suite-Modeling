import { useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { analyzeDocument, fetchRemediationBacklog, recommendMethodology } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { Badge } from "../components/ui/Badge";
import { Alert } from "../components/ui/Alert";
import { METHODOLOGY_META } from "../constants/methodologyMeta";
import { FRAMEWORK_LABELS } from "../constants/frameworkLabels";
import { useSession } from "../context/SessionContext";
import { filterActiveThreats, listFrameworksFromAnalysisThreats } from "../utils/analysisFilters";
import type {
  HeuristicThreat,
  MethodologyRecommendation,
  RemediationBacklogResponse,
} from "../types/api";
import type { MethodologyId } from "../types/methodology";

export function AnalysisPage() {
  const { document, analysis, setAnalysis } = useSession();
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
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha na análise.");
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
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao gerar backlog.");
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
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao recomendar metodologia.");
    } finally {
      setRecommending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Análise</h1>
        <p className="mt-1 text-sm text-slate-600">
          Motor STRIDE, fronteiras de confiança e risco (L×I). Referências a frameworks vêm do
          servidor.
        </p>
      </div>

      <Card title="Executar motor">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="sm:w-64">
            <Label htmlFor="methodology">Metodologia</Label>
            <Select
              id="methodology"
              value={methodology}
              onChange={(e) =>
                setMethodology(
                  e.target.value as MethodologyId,
                )
              }
            >
              <option value="stride">STRIDE (default)</option>
              <option value="linddun">LINDDUN (privacidade)</option>
              <option value="nist_data_centric">NIST Data-Centric</option>
              <option value="octave_allegro">OCTAVE Allegro</option>
              <option value="cia_die">CIA / CIA-DIE</option>
              <option value="pasta">PASTA (avançado/risk-centric)</option>
              <option value="plot4ai">PLOT4ai (AI/LLM)</option>
            </Select>
            <p className="mt-1 text-xs text-slate-500">
              {METHODOLOGY_META[methodology].hint}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5">
                Category: {METHODOLOGY_META[methodology].category}
              </span>
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5">
                Best for: {METHODOLOGY_META[methodology].bestFor}
              </span>
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5">
                Maturity: {METHODOLOGY_META[methodology].maturity}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Pode recomendar automaticamente e ainda assim fazer override manual.
            </p>
          </div>
          <div className="flex-1">
            <Label htmlFor="pack">Industry pack (opcional)</Label>
            <Input
              id="pack"
              placeholder="ex.: finance"
              value={packId}
              onChange={(e) => setPackId(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">Deixe vazio para análise só com heurísticas base.</p>
          </div>
          <Button variant="secondary" onClick={() => void recommend()} disabled={recommending}>
            {recommending ? "A recomendar…" : "Recomendar metodologia"}
          </Button>
          <Button onClick={() => void run()} disabled={loading}>
            {loading ? "A analisar…" : "Gerar análise"}
          </Button>
        </div>
        {recommendation && (
          <div className="mt-3 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
            <p className="font-medium">
              Recomendação: {recommendation.methodology}
            </p>
            <p className="mt-1">{recommendation.reason}</p>
            {recommendation.explanations && recommendation.explanations.length > 0 ? (
              <details className="mt-2 text-xs text-sky-950">
                <summary className="cursor-pointer font-medium text-sky-900">Contexto da recomendação</summary>
                <ul className="mt-1 list-inside list-disc text-sky-900/90">
                  {recommendation.explanations.slice(0, 4).map((e) => (
                    <li key={e.id}>{e.message}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        )}
      </Card>

      {error && <Alert>{error}</Alert>}

      {analysis && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Heurísticas novas"
              value={String(analysis.summary.heuristic_threats_generated)}
            />
            <Stat
              label="Já cobertas"
              value={String(analysis.summary.heuristic_threats_skipped_duplicate)}
            />
            <Stat
              label="Maior L×I"
              value={
                analysis.summary.max_risk_score == null
                  ? "—"
                  : String(analysis.summary.max_risk_score)
              }
            />
            <Stat label="Motor" value={analysis.engine_version} small />
            <Stat label="Metodologia" value={analysis.methodology} small />
          </div>
          {analysis.methodology === "plot4ai" && analysis.ai_system_context ? (
            <Card
              title="PLOT4ai — sistema com IA"
              subtitle="Deteção heurística a partir do modelo; não substitui revisão de arquitectura."
            >
              <p className="text-sm text-slate-800">{analysis.ai_system_context.synopsis}</p>
              {analysis.ai_system_context.pattern_tags.length > 0 ? (
                <p className="mt-2 text-xs text-slate-600">
                  <span className="font-medium text-slate-700">Padrões:</span>{" "}
                  {analysis.ai_system_context.pattern_tags.join(", ")}
                </p>
              ) : null}
              {analysis.ai_system_context.primary_risk_surfaces.length > 0 ? (
                <div className="mt-3">
                  <p className="text-xs font-medium text-slate-800">Superfícies de risco</p>
                  <ul className="mt-1 list-inside list-disc text-xs text-slate-700">
                    {analysis.ai_system_context.primary_risk_surfaces.slice(0, 4).map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {analysis.ai_system_context.prioritized_recommendations.length > 0 ? (
                <details className="mt-3 text-xs text-slate-700">
                  <summary className="cursor-pointer font-medium text-slate-800">
                    Acções prioritárias (IA)
                  </summary>
                  <ul className="mt-1 list-inside list-disc">
                    {analysis.ai_system_context.prioritized_recommendations.slice(0, 5).map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </Card>
          ) : null}
          {analysis.methodology_recommendation_reason && (
            <Alert variant="info">
              Recomendação aplicada: {analysis.methodology_recommendation_reason}
            </Alert>
          )}
          {analysis.explanations && analysis.explanations.length > 0 ? (
            <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-sm text-slate-800">
              <summary className="cursor-pointer font-medium text-slate-900">Explicabilidade do resultado</summary>
              <p className="mt-2 text-xs text-slate-600">
                Motivos estruturados gerados pelo motor (máx. 8 linhas; o JSON completo tem o resto).
              </p>
              <div className="mt-2 max-w-xs">
                <Label htmlFor="expCategory">Categoria</Label>
                <Select
                  id="expCategory"
                  value={explanationCategoryFilter}
                  onChange={(e) => setExplanationCategoryFilter(e.target.value)}
                >
                  <option value="">Todas</option>
                  {explanationCategories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </div>
              <ul className="mt-2 space-y-1.5 text-xs text-slate-700">
                {visibleExplanations.slice(0, 8).map((e) => (
                  <li key={e.id}>
                    <span className="font-medium text-slate-800">{e.subject}:</span> {e.message}
                  </li>
                ))}
              </ul>
              {visibleExplanations.length === 0 ? (
                <p className="mt-2 text-xs text-slate-500">Sem explicações para esta categoria.</p>
              ) : null}
            </details>
          ) : null}

          <Card
            title="Backlog de remediação (sugerido)"
            subtitle="Priorização heurística com racional — não é gestor de tarefas."
          >
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => void loadBacklog()}
                disabled={backlogLoading}
              >
                {backlogLoading ? "A gerar…" : "Gerar vista de backlog"}
              </Button>
            </div>
            {backlog && (
              <div className="mt-4 space-y-4 text-sm text-slate-700">
                <p className="text-slate-600">{backlog.executive_summary}</p>
                {backlog.synergy_notes.length > 0 && (
                  <div>
                    <p className="font-medium text-slate-800">Agrupamentos / sinergia</p>
                    <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
                      {backlog.synergy_notes.slice(0, 4).map((n) => (
                        <li key={n}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  <p className="font-medium text-slate-800">Top acções</p>
                  <ul className="mt-1 space-y-2">
                    {backlog.top_5_action_ids.map((id) => {
                      const it = backlog.items.find((x) => x.id === id);
                      if (!it) return null;
                      return (
                        <li key={id} className="rounded border border-slate-100 bg-slate-50 px-2 py-1.5">
                          <span className="font-medium text-slate-900">{it.title}</span>
                          <span className="text-slate-500">
                            {" "}
                            · {it.priority_label} · esforço {it.effort_estimate}
                          </span>
                          {it.explanations?.[0] ? (
                            <p className="mt-1 text-[11px] leading-snug text-slate-600">
                              {it.explanations[0].message}
                            </p>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                </div>
                {backlog.quick_win_ids.length > 0 && (
                  <div>
                    <p className="font-medium text-slate-800">Quick wins</p>
                    <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
                      {backlog.quick_win_ids.slice(0, 6).map((id) => {
                        const it = backlog.items.find((x) => x.id === id);
                        return <li key={id}>{it?.title ?? id}</li>;
                      })}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Card>
          {analysis.methodology_insights?.blocks?.length ? (
            <Card
              title="Insights da metodologia"
              subtitle={
                analysis.methodology_insights.profile ?? "Complementos específicos da metodologia escolhida."
              }
            >
              <div className="grid gap-3 sm:grid-cols-2">
                {analysis.methodology_insights.blocks.slice(0, 6).map((b) => (
                  <div key={b.key} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-sm font-semibold text-slate-900">{b.title}</p>
                    <ul className="mt-2 space-y-1 text-xs text-slate-600">
                      {b.items.slice(0, 3).map((item) => (
                        <li key={item}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}

          <Card
            title="Ameaças sugeridas"
            subtitle="Filtre por pontuação ou por catálogo de framework."
          >
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="sm:w-48">
                <Label htmlFor="minScore">Pontuação mínima (L×I)</Label>
                <Input
                  id="minScore"
                  type="number"
                  min={0}
                  max={25}
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value) || 0)}
                />
              </div>
              <div className="sm:w-56">
                <Label htmlFor="fw">Framework</Label>
                <Select
                  id="fw"
                  value={frameworkFilter}
                  onChange={(e) => setFrameworkFilter(e.target.value)}
                >
                  <option value="">Todos</option>
                  {frameworks.map((fw) => (
                    <option key={fw} value={fw}>
                      {FRAMEWORK_LABELS[fw] ?? fw}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <p className="mb-3 text-xs text-slate-500">
              A mostrar {filtered.length} de{" "}
              {analysis.heuristic_threats.filter((h) => !h.skipped_as_duplicate).length} ameaças
              ativas.
            </p>
            <ul className="divide-y divide-slate-100">
              {filtered.map((h) => (
                <li key={h.id} className="py-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-slate-900">{h.title}</p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {h.target_component_id && <>Componente: {h.target_component_id} · </>}
                        {h.target_data_flow_id && <>Fluxo: {h.target_data_flow_id} · </>}
                        STRIDE: {h.stride}
                      </p>
                    </div>
                    <Badge tone="warn">score {h.risk.score ?? "—"}</Badge>
                  </div>
                  {(h.framework_refs?.length ?? 0) > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {h.framework_refs.map((r) => (
                        <Badge key={`${h.id}:${r.framework}:${r.control_id}`} tone="accent">
                          {FRAMEWORK_LABELS[r.framework] ?? r.framework}:{r.control_id}
                        </Badge>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
            {filtered.length === 0 && (
              <p className="py-6 text-center text-sm text-slate-500">
                Nenhuma ameaça corresponde aos filtros.
              </p>
            )}
          </Card>

          <div className="flex justify-end">
            <Link to="/export">
              <Button>Exportar resultados</Button>
            </Link>
          </div>
        </>
      )}

      {analysis === null && (
        <p className="text-sm text-slate-500">
          Ainda não há resultado. Carregue em <strong>Gerar análise</strong>.
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  small,
}: Readonly<{
  label: string;
  value: string;
  small?: boolean;
}>) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-0.5 font-semibold text-slate-900 ${small ? "text-sm" : "text-lg"}`}>
        {value}
      </p>
    </div>
  );
}
