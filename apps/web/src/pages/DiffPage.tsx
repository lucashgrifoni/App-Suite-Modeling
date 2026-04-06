import { useCallback, useState } from "react";
import { Navigate } from "react-router-dom";
import { compareThreatModels } from "../api/otmApi";
import { ApiError } from "../api/client";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Checkbox } from "../components/ui/Checkbox";
import { Input } from "../components/ui/Input";
import { Label } from "../components/ui/Label";
import { PageHeader } from "../components/patterns/PageHeader";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { HelpCallout } from "../components/onboarding/HelpCallout";
import { RiskScoreBar } from "../components/analytics/RiskScoreBar";
import { StatusPill } from "../components/ui/StatusPill";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import type { ComparisonMeta, DiffAggregateSection, ThreatModelComparisonResult } from "../types/api";
import type { OtmDocument } from "../types/document";

function parseRevisedJson(raw: string): OtmDocument {
  const data = JSON.parse(raw) as unknown;
  if (!data || typeof data !== "object") throw new Error("JSON inválido.");
  const d = data as OtmDocument;
  if (!d.model || !d.metadata) throw new Error("Esperado objeto com `model` e `metadata` (documento canónico).");
  return d;
}

function previewIds(ids: string[], limit = 8): string {
  if (ids.length <= limit) return ids.join(", ");
  return `${ids.slice(0, limit).join(", ")}… (+${ids.length - limit})`;
}

function AggregateBlock({
  title,
  section,
}: Readonly<{
  title: string;
  section: DiffAggregateSection | undefined;
}>) {
  const added = section?.added ?? [];
  const removed = section?.removed ?? [];
  const changed = section?.changed ?? [];
  if (added.length === 0 && removed.length === 0 && changed.length === 0) return null;
  return (
    <div className="rounded-otm-lg border border-otm-border bg-gradient-to-br from-otm-surface-1/95 to-otm-surface-2/80 p-4 text-xs text-otm-text shadow-otm-sm">
      <div className="flex items-center justify-between gap-2 border-b border-otm-border/80 pb-2 font-display text-sm font-semibold text-otm-text">
        {title}
        <span className="text-[10px] font-normal uppercase tracking-wide text-otm-text-subtle">
          {added.length + removed.length + changed.length} alterações
        </span>
      </div>
      <div className="mt-3 space-y-2.5">
        {added.length ? (
          <div className="rounded-otm-md border border-emerald-500/25 bg-emerald-950/20 px-2.5 py-2">
            <p className="flex flex-wrap items-baseline gap-2">
              <StatusPill tone="success">+{added.length} adicionados</StatusPill>
              <span className="text-otm-text-muted">{previewIds(added)}</span>
            </p>
          </div>
        ) : null}
        {removed.length ? (
          <div className="rounded-otm-md border border-red-500/25 bg-red-950/20 px-2.5 py-2">
            <p className="flex flex-wrap items-baseline gap-2">
              <StatusPill tone="danger">−{removed.length} removidos</StatusPill>
              <span className="text-otm-text-muted">{previewIds(removed)}</span>
            </p>
          </div>
        ) : null}
        {changed.length ? (
          <div className="rounded-otm-md border border-amber-500/25 bg-amber-950/15 px-2.5 py-2">
            <p className="flex flex-wrap items-baseline gap-2">
              <StatusPill tone="warning">~{changed.length} alterados</StatusPill>
              <span className="text-otm-text-muted">{previewIds(changed)}</span>
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function DiffSummaryCard({
  summary,
  structuralLine,
  runAnalysis,
  maxRev,
  maxBase,
}: Readonly<{
  summary: ThreatModelComparisonResult["summary"];
  structuralLine: string;
  runAnalysis: boolean;
  maxRev: number | null | undefined;
  maxBase: number | null | undefined;
}>) {
  return (
    <Card className="space-y-4 p-5" variant="glass">
      <h2 className="font-display text-sm font-semibold text-otm-text">Resumo</h2>
      <p className="text-base font-medium leading-relaxed text-otm-text">{summary.headline}</p>
      <p className="text-sm text-otm-text-muted">{structuralLine}</p>
      <div className="flex flex-wrap gap-2">
        {summary.has_structural_changes ? <Badge tone="accent">Estrutura</Badge> : null}
        {summary.has_analysis_changes ? <Badge tone="accent">Análise</Badge> : null}
        {summary.methodology_in_model_changed ? <Badge tone="warn">Metodologia (modelo)</Badge> : null}
      </div>
      {runAnalysis && typeof maxRev === "number" ? (
        <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/70 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">Maior L×I (revisão)</p>
          <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-otm-text">{maxRev}</p>
          {typeof maxBase === "number" ? (
            <p className="mt-0.5 text-xs text-otm-text-muted">Baseline: {maxBase}</p>
          ) : null}
          <RiskScoreBar score={maxRev} className="mt-3" caption="Leitura rápida do pico de risco na revisão." />
        </div>
      ) : null}
    </Card>
  );
}

function DiffRiskDeltaCard({
  rd,
  runAnalysis,
}: Readonly<{
  rd: ThreatModelComparisonResult["risk_delta"];
  runAnalysis: boolean;
}>) {
  const hasDelta =
    runAnalysis &&
    (typeof rd.analysis_max_score_delta === "number" ||
      (rd.heuristic_increased_ids?.length ?? 0) > 0 ||
      (rd.heuristic_decreased_ids?.length ?? 0) > 0);
  if (!hasDelta) return null;
  return (
    <Card className="space-y-3 p-5" variant="elevated">
      <h2 className="font-display text-sm font-semibold text-otm-text">Top deltas de risco (análise)</h2>
      {typeof rd.analysis_max_score_delta === "number" ? (
        <p className="text-sm text-otm-text-muted">
          Δ score máximo (revisão − baseline):{" "}
          <strong className="text-otm-text">
            {rd.analysis_max_score_delta >= 0 ? "+" : ""}
            {rd.analysis_max_score_delta.toFixed(2)}
          </strong>{" "}
          (antes {rd.analysis_max_score_baseline ?? "—"} → depois {rd.analysis_max_score_revised ?? "—"})
        </p>
      ) : null}
      {(rd.heuristic_increased_ids?.length ?? 0) > 0 ? (
        <p className="text-xs text-red-200">
          Scores que subiram (heurísticas): {previewIds(rd.heuristic_increased_ids ?? [])}
        </p>
      ) : null}
      {(rd.heuristic_decreased_ids?.length ?? 0) > 0 ? (
        <p className="text-xs text-emerald-200">Scores que desceram: {previewIds(rd.heuristic_decreased_ids ?? [])}</p>
      ) : null}
    </Card>
  );
}

function SemanticDiffSectionsBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const raw = meta.semantic_diff_sections;
  if (!raw || typeof raw !== "object") return null;
  const sec = raw as {
    structural_change_summary?: string[];
    improved?: string[];
    worsened?: string[];
    risk_impact?: string[];
  };
  const scs = sec.structural_change_summary ?? [];
  const imp = sec.improved ?? [];
  const wor = sec.worsened ?? [];
  const risk = sec.risk_impact ?? [];
  if (scs.length === 0 && imp.length === 0 && wor.length === 0 && risk.length === 0) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {scs.length ? (
        <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 text-xs text-otm-text-muted sm:col-span-3">
          <p className="font-semibold text-otm-text">Mudança estrutural (contagens)</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {scs.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {imp.length ? (
        <div className="rounded-otm-md border border-emerald-500/20 bg-emerald-950/15 p-3 text-xs text-otm-text-muted">
          <p className="font-semibold text-emerald-100">Melhorou</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {imp.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {wor.length ? (
        <div className="rounded-otm-md border border-amber-500/20 bg-amber-950/15 p-3 text-xs text-otm-text-muted">
          <p className="font-semibold text-amber-100">Piorou / atenção</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {wor.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {risk.length ? (
        <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 text-xs text-otm-text-muted sm:col-span-3 lg:col-span-1">
          <p className="font-semibold text-otm-text">Impacto de risco</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {risk.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function StructuralRefsBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const refs = meta.semantic_structural_refs ?? [];
  if (!refs.length) return null;
  return (
    <div data-testid="diff-structural-refs">
      <Card className="space-y-2 p-4" variant="glass">
        <h2 className="font-display text-sm font-semibold text-otm-text">Estrutura → interpretação</h2>
        <p className="text-xs text-otm-text-muted">
          Referências correlacionais (ref:struct:*). Não implicam causalidade provada entre mudança e incidente.
        </p>
        <ul className="list-inside list-disc space-y-1.5 text-xs text-otm-text-muted">
          {refs.slice(0, 12).map((r) => (
            <li key={r.ref}>
              <span className="font-mono text-otm-accent">{r.ref}</span> · {r.entity_kind}{" "}
              <span className="text-otm-text">{r.entity_id}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function SemanticInsightsBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const raw = meta.semantic_insights;
  const insights = Array.isArray(raw) ? (raw as string[]) : [];
  const ver = typeof meta.semantic_insights_version === "string" ? meta.semantic_insights_version : "";
  const disc = typeof meta.interpretation_disclaimer === "string" ? meta.interpretation_disclaimer : "";
  const hasSections =
    meta.semantic_diff_sections != null && typeof meta.semantic_diff_sections === "object";
  if (insights.length === 0 && !hasSections) return null;
  return (
    <div data-testid="diff-semantic-panel">
    <Card className="space-y-2 p-4" variant="elevated">
      <h2 className="font-display text-sm font-semibold text-otm-text">Diff semântico</h2>
      {ver ? (
        <p className="text-[10px] uppercase tracking-wide text-otm-text-subtle">Versão {ver}</p>
      ) : null}
      {disc ? <p className="text-xs italic text-otm-text-muted">{disc}</p> : null}
      <SemanticDiffSectionsBlock meta={meta} />
      {insights.length > 0 ? (
        <ul className="list-inside list-disc space-y-1.5 text-sm text-otm-text-muted">
          {insights.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </Card>
    </div>
  );
}

function ComparisonResultPanel({
  result,
  runAnalysis,
}: Readonly<{
  result: ThreatModelComparisonResult;
  runAnalysis: boolean;
}>) {
  const rd = result.risk_delta;
  const maxRev = rd.analysis_max_score_revised;
  const maxBase = rd.analysis_max_score_baseline;
  return (
    <div className="space-y-4">
      <DiffSummaryCard
        summary={result.summary}
        structuralLine={result.structural.summary_line}
        runAnalysis={runAnalysis}
        maxRev={maxRev}
        maxBase={maxBase}
      />

      {result.key_insights.length ? (
        <Card className="space-y-2 p-4" variant="elevated">
          <h2 className="font-display text-sm font-semibold text-otm-text">Insights principais</h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-otm-text-muted">
            {result.key_insights.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      {result.explanations && result.explanations.length > 0 ? (
        <details className="rounded-otm-lg border border-otm-border bg-otm-surface-2 p-4 text-sm text-otm-text">
          <summary className="cursor-pointer font-semibold">Porquê (diff estruturado)</summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
            {result.explanations.slice(0, 6).map((e) => (
              <li key={e.id}>
                <span className="font-medium text-otm-text">{e.subject}:</span> {e.message}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <Card className="space-y-3 p-5" variant="glass">
        <h2 className="font-display text-sm font-semibold text-otm-text">Mudanças por secção (IDs)</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <AggregateBlock title="Componentes" section={result.aggregate.components} />
          <AggregateBlock title="Ativos" section={result.aggregate.assets} />
          <AggregateBlock title="Fluxos de dados" section={result.aggregate.data_flows} />
          <AggregateBlock title="Trust boundaries" section={result.aggregate.trust_boundaries} />
          <AggregateBlock title="Ameaças (canónicas)" section={result.aggregate.threats} />
          <AggregateBlock title="Mitigações" section={result.aggregate.mitigations} />
        </div>
      </Card>

      <DiffRiskDeltaCard rd={rd} runAnalysis={runAnalysis} />

      <SemanticInsightsBlock meta={result.meta} />

      <StructuralRefsBlock meta={result.meta} />

      <Card className="space-y-2 p-4" variant="glass">
        <h2 className="font-display text-sm font-semibold text-otm-text">JSON completo</h2>
        <pre className="max-h-[360px] overflow-auto rounded-otm-md bg-otm-green-950 p-3 text-xs text-otm-mint-300">
          {JSON.stringify(result, null, 2)}
        </pre>
      </Card>
    </div>
  );
}

export function DiffPage() {
  const { document: baseline } = useSession();
  const toast = useToast();
  const [revisedText, setRevisedText] = useState("");
  const [runAnalysis, setRunAnalysis] = useState(false);
  const [packId, setPackId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ThreatModelComparisonResult | null>(null);

  const onFile = useCallback((file: File | null) => {
    if (!file) return;
    const r = new FileReader();
    r.onload = () => {
      setRevisedText(typeof r.result === "string" ? r.result : "");
      setResult(null);
      setError(null);
    };
    r.readAsText(file, "UTF-8");
  }, []);

  if (!baseline) return <Navigate to="/" replace />;

  async function runDiff() {
    const base = baseline;
    if (!base) return;
    setError(null);
    setResult(null);
    let revised: OtmDocument;
    try {
      revised = parseRevisedJson(revisedText.trim() || "{}");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Falha ao interpretar JSON da revisão.";
      setError(msg);
      toast.error(msg);
      return;
    }
    setLoading(true);
    try {
      const d = await compareThreatModels(base, revised, {
        runAnalysis,
        packId: packId.trim() || null,
      });
      setResult(d);
      toast.success("Comparação concluída.");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Falha ao pedir comparação à API.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Comparação semântica"
        title="Diff entre versões"
        description={
          <>
            A <strong className="text-otm-text">baseline</strong> é o modelo atual da sessão. Cole ou carregue a{" "}
            <strong className="text-otm-text">revisão</strong> em JSON (mesmo formato que exportação{" "}
            <code className="rounded bg-otm-surface-3 px-1 text-xs text-otm-accent">document_json</code>). O servidor
            devolve diff estrutural semântico, agregados e — se pedido — deltas de análise.
          </>
        }
      />

      <div className="space-y-3 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <HelpCallout title="Baseline vs revisão">
          A sessão atual é a <strong className="text-otm-text">baseline</strong>. Cole JSON exportado como revisão
          para comparar evolução estrutural e, opcionalmente, deltas do motor.
        </HelpCallout>
      </div>

      <Card className="space-y-3 p-4" variant="elevated">
        <div>
          <Label htmlFor="revised-json">Revisão (JSON)</Label>
          <textarea
            id="revised-json"
            className="mt-1 min-h-[180px] w-full rounded-otm-md border border-otm-border bg-otm-surface-1 px-3 py-2 font-mono text-xs text-otm-text placeholder:text-otm-text-subtle focus:border-otm-mint-400/50 focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)]"
            value={revisedText}
            onChange={(ev) => setRevisedText(ev.target.value)}
            placeholder='{ "model": { ... }, "metadata": { ... }, ... }'
          />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-otm-text-muted">
            <Checkbox checked={runAnalysis} onChange={(e) => setRunAnalysis(e.target.checked)} />
            Incluir análise (executa o motor nos dois documentos no servidor)
          </label>
        </div>
        {runAnalysis ? (
          <div>
            <Label htmlFor="pack-id">Pack (opcional)</Label>
            <Input
              id="pack-id"
              className="mt-1 max-w-md font-mono text-sm"
              value={packId}
              onChange={(e) => setPackId(e.target.value)}
              placeholder="ex.: healthcare"
            />
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="file"
            accept=".json,application/json"
            className="text-sm text-otm-text-muted file:mr-2"
            onChange={(ev) => onFile(ev.target.files?.[0] ?? null)}
          />
          <Button type="button" onClick={() => void runDiff()} disabled={loading || !revisedText.trim()}>
            {loading ? "A comparar…" : "Comparar"}
          </Button>
        </div>
      </Card>

      {error ? <Alert variant="error">{error}</Alert> : null}

      {result ? <ComparisonResultPanel result={result} runAnalysis={runAnalysis} /> : null}
    </div>
  );
}
