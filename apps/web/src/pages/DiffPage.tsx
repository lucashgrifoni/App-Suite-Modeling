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
import { useSession } from "../context/SessionContext";
import type { DiffAggregateSection, ThreatModelComparisonResult } from "../types/api";
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
    <div className="rounded-md border border-slate-100 bg-slate-50/80 p-3 text-xs text-slate-800">
      <div className="font-semibold text-slate-900">{title}</div>
      {added.length ? (
        <p className="mt-1">
          <span className="font-medium text-emerald-800">+{added.length}</span>{" "}
          <span className="text-slate-600">{previewIds(added)}</span>
        </p>
      ) : null}
      {removed.length ? (
        <p className="mt-1">
          <span className="font-medium text-rose-800">−{removed.length}</span>{" "}
          <span className="text-slate-600">{previewIds(removed)}</span>
        </p>
      ) : null}
      {changed.length ? (
        <p className="mt-1">
          <span className="font-medium text-amber-800">~{changed.length}</span>{" "}
          <span className="text-slate-600">{previewIds(changed)}</span>
        </p>
      ) : null}
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
  return (
    <div className="space-y-4">
      <Card className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-slate-900">Resumo</h2>
        <p className="text-sm text-slate-800">{result.summary.headline}</p>
        <p className="text-sm text-slate-600">{result.structural.summary_line}</p>
        <div className="flex flex-wrap gap-2">
          {result.summary.has_structural_changes ? <Badge tone="accent">Estrutura</Badge> : null}
          {result.summary.has_analysis_changes ? <Badge tone="accent">Análise</Badge> : null}
          {result.summary.methodology_in_model_changed ? <Badge tone="warn">Metodologia (modelo)</Badge> : null}
        </div>
      </Card>

      {result.key_insights.length ? (
        <Card className="space-y-2 p-4">
          <h2 className="text-sm font-semibold text-slate-900">Insights principais</h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-800">
            {result.key_insights.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      {result.explanations && result.explanations.length > 0 ? (
        <details className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-800">
          <summary className="cursor-pointer font-semibold text-slate-900">Porquê (diff estruturado)</summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-700">
            {result.explanations.slice(0, 6).map((e) => (
              <li key={e.id}>
                <span className="font-medium text-slate-800">{e.subject}:</span> {e.message}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <Card className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-slate-900">Mudanças por secção (IDs)</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          <AggregateBlock title="Componentes" section={result.aggregate.components} />
          <AggregateBlock title="Ativos" section={result.aggregate.assets} />
          <AggregateBlock title="Fluxos de dados" section={result.aggregate.data_flows} />
          <AggregateBlock title="Trust boundaries" section={result.aggregate.trust_boundaries} />
          <AggregateBlock title="Ameaças (canónicas)" section={result.aggregate.threats} />
          <AggregateBlock title="Mitigações" section={result.aggregate.mitigations} />
        </div>
      </Card>

      {runAnalysis &&
      (typeof rd.analysis_max_score_delta === "number" ||
        (rd.heuristic_increased_ids?.length ?? 0) > 0 ||
        (rd.heuristic_decreased_ids?.length ?? 0) > 0) ? (
        <Card className="space-y-2 p-4">
          <h2 className="text-sm font-semibold text-slate-900">Top deltas de risco (análise)</h2>
          {typeof rd.analysis_max_score_delta === "number" ? (
            <p className="text-sm text-slate-800">
              Δ score máximo (revisão − baseline):{" "}
              <strong>{rd.analysis_max_score_delta >= 0 ? "+" : ""}{rd.analysis_max_score_delta.toFixed(2)}</strong> (antes{" "}
              {rd.analysis_max_score_baseline ?? "—"} → depois {rd.analysis_max_score_revised ?? "—"})
            </p>
          ) : null}
          {(rd.heuristic_increased_ids?.length ?? 0) > 0 ? (
            <p className="text-xs text-rose-900">
              Scores que subiram (heurísticas): {previewIds(rd.heuristic_increased_ids ?? [])}
            </p>
          ) : null}
          {(rd.heuristic_decreased_ids?.length ?? 0) > 0 ? (
            <p className="text-xs text-emerald-900">Scores que desceram: {previewIds(rd.heuristic_decreased_ids ?? [])}</p>
          ) : null}
        </Card>
      ) : null}

      <Card className="space-y-2 p-4">
        <h2 className="text-sm font-semibold text-slate-900">JSON completo</h2>
        <pre className="max-h-[360px] overflow-auto rounded-md bg-slate-50 p-3 text-xs text-slate-800">
          {JSON.stringify(result, null, 2)}
        </pre>
      </Card>
    </div>
  );
}

export function DiffPage() {
  const { document: baseline } = useSession();
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
      setError(e instanceof Error ? e.message : "Falha ao interpretar JSON da revisão.");
      return;
    }
    setLoading(true);
    try {
      const d = await compareThreatModels(base, revised, {
        runAnalysis,
        packId: packId.trim() || null,
      });
      setResult(d);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao pedir comparação à API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Diff entre versões</h1>
        <p className="mt-1 text-sm text-slate-600">
          A <strong>baseline</strong> é o modelo atual da sessão. Cole ou carregue a <strong>revisão</strong> em JSON
          (mesmo formato que exportação <code className="text-xs">document_json</code>). O servidor devolve diff
          estrutural semântico, agregados e — se pedido — deltas de análise.
        </p>
      </div>

      <Card className="space-y-3 p-4">
        <div>
          <Label htmlFor="revised-json">Revisão (JSON)</Label>
          <textarea
            id="revised-json"
            className="mt-1 min-h-[180px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 font-mono text-xs text-slate-800"
            value={revisedText}
            onChange={(ev) => setRevisedText(ev.target.value)}
            placeholder='{ "model": { ... }, "metadata": { ... }, ... }'
          />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
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
            className="text-sm text-slate-600"
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
