import { useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { analyzeDocument, recommendMethodology } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { Select } from "../components/ui/Select";
import { Badge } from "../components/ui/Badge";
import { Alert } from "../components/ui/Alert";
import { useSession } from "../context/SessionContext";
import type { HeuristicThreat, MethodologyRecommendation } from "../types/api";

const FRAMEWORK_LABELS: Record<string, string> = {
  owasp_tm: "OWASP TM",
  owasp_asvs: "OWASP ASVS",
  nist_csf: "NIST CSF",
  iso_27001: "ISO 27001",
};

type MethodologyId =
  | "stride"
  | "linddun"
  | "nist_data_centric"
  | "octave_allegro"
  | "cia_die"
  | "pasta"
  | "plot4ai";

const METHODOLOGY_META: Record<
  MethodologyId,
  {
    hint: string;
    bestFor: string;
    maturity: "Mature" | "Evolving" | "Specialized" | "Experimental";
    category: string;
  }
> = {
  stride: {
    hint: "Default técnico e mais maduro para web/API/cloud.",
    bestFor: "Web, API, cloud-native",
    maturity: "Mature",
    category: "General security",
  },
  linddun: {
    hint: "Privacidade: PII, consentimento, minimização e conformidade.",
    bestFor: "LGPD/GDPR e dados pessoais",
    maturity: "Evolving",
    category: "Privacy",
  },
  nist_data_centric: {
    hint: "Proteção de dados críticos e caminhos sensíveis.",
    bestFor: "Dados críticos/classificados",
    maturity: "Evolving",
    category: "Data-centric",
  },
  octave_allegro: {
    hint: "Risco de negócio orientado a ativos.",
    bestFor: "Ativos e risco organizacional",
    maturity: "Evolving",
    category: "Business risk",
  },
  cia_die: {
    hint: "Análise rápida e comunicação executiva.",
    bestFor: "Workshops rápidos",
    maturity: "Evolving",
    category: "Executive",
  },
  pasta: {
    hint: "Análise avançada risk-centric (ataque, vulnerabilidade, impacto).",
    bestFor: "Contextos enterprise avançados",
    maturity: "Specialized",
    category: "Advanced risk",
  },
  plot4ai: {
    hint: "Ameaças de IA/LLM (prompt, RAG, agentes, inferência).",
    bestFor: "Sistemas AI/LLM",
    maturity: "Specialized",
    category: "AI/LLM",
  },
};

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

  const doc = document;

  const frameworks = useMemo(() => {
    if (!analysis) return [];
    const s = new Set<string>();
    for (const h of analysis.heuristic_threats) {
      if (h.skipped_as_duplicate) continue;
      for (const r of h.framework_refs ?? []) s.add(r.framework);
    }
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [analysis]);

  const filtered: HeuristicThreat[] = useMemo(() => {
    if (!analysis) return [];
    return analysis.heuristic_threats.filter((h) => {
      if (h.skipped_as_duplicate) return false;
      const score = h.risk.score ?? 0;
      if (score < minScore) return false;
      if (frameworkFilter) {
        const has = (h.framework_refs ?? []).some((r) => r.framework === frameworkFilter);
        if (has === false) return false;
      }
      return true;
    });
  }, [analysis, minScore, frameworkFilter]);

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
          {analysis.methodology_recommendation_reason && (
            <Alert variant="info">
              Recomendação aplicada: {analysis.methodology_recommendation_reason}
            </Alert>
          )}
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
