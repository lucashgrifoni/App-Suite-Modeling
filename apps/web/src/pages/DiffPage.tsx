import { useCallback, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import { compareThreatModels } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
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
import i18n from "../i18n/i18n";
import type { ComparisonMeta, DiffAggregateSection, ThreatModelComparisonResult } from "../types/api";
import type { OtmDocument } from "../types/document";

function parseRevisedJson(raw: string): OtmDocument {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(i18n.t("diff.invalidJson"));
  }
  if (!data || typeof data !== "object") {
    throw new Error(i18n.t("diff.invalidJson"));
  }
  const d = data as OtmDocument;
  if (!d.model || !d.metadata) {
    throw new Error(i18n.t("diff.expectedDoc"));
  }
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
  const { t } = useTranslation();
  const added = section?.added ?? [];
  const removed = section?.removed ?? [];
  const changed = section?.changed ?? [];
  // Same predicate the parent card filters on, so the two can never disagree about
  // whether a section is empty.
  if (!sectionHasChanges(section)) return null;
  const total = added.length + removed.length + changed.length;
  return (
    <div className="rounded-otm-lg border border-otm-border bg-gradient-to-br from-otm-surface-1/95 to-otm-surface-2/80 p-4 text-xs text-otm-text shadow-otm-sm">
      <div className="flex items-center justify-between gap-2 border-b border-otm-border/80 pb-2 font-display text-sm font-semibold text-otm-text">
        {title}
        <span className="text-[10px] font-normal uppercase tracking-wide text-otm-text-subtle">
          {total} {t("diff.changes")}
        </span>
      </div>
      <div className="mt-3 space-y-2.5">
        {added.length ? (
          <div className="rounded-otm-md border border-emerald-500/25 bg-emerald-950/20 px-2.5 py-2">
            <p className="flex flex-wrap items-baseline gap-2">
              <StatusPill tone="success">{t("diff.added", { count: added.length })}</StatusPill>
              <span className="text-otm-text-muted">{previewIds(added)}</span>
            </p>
          </div>
        ) : null}
        {removed.length ? (
          <div className="rounded-otm-md border border-red-500/25 bg-red-950/20 px-2.5 py-2">
            <p className="flex flex-wrap items-baseline gap-2">
              <StatusPill tone="danger">{t("diff.removed", { count: removed.length })}</StatusPill>
              <span className="text-otm-text-muted">{previewIds(removed)}</span>
            </p>
          </div>
        ) : null}
        {changed.length ? (
          <div className="rounded-otm-md border border-amber-500/25 bg-amber-950/15 px-2.5 py-2">
            <p className="flex flex-wrap items-baseline gap-2">
              <StatusPill tone="warning">{t("diff.changed", { count: changed.length })}</StatusPill>
              <span className="text-otm-text-muted">{previewIds(changed)}</span>
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function sectionHasChanges(section: DiffAggregateSection | undefined): boolean {
  if (!section) return false;
  return [section.added, section.removed, section.changed].some((ids) => (ids?.length ?? 0) > 0);
}

/**
 * "Changes by section (IDs)" delegated to six `AggregateBlock`s, each of which renders
 * nothing when its section is untouched. Comparing a model against an identical revision
 * therefore produced a card with a heading and a completely empty body — indistinguishable,
 * to the reader, from a section that failed to load.
 */
function AggregateSectionsCard({
  aggregate,
}: Readonly<{ aggregate: ThreatModelComparisonResult["aggregate"] }>) {
  const { t } = useTranslation();
  const sections: { key: string; title: string; section: DiffAggregateSection | undefined }[] = [
    { key: "components", title: t("diff.aggComponents"), section: aggregate.components },
    { key: "assets", title: t("diff.aggAssets"), section: aggregate.assets },
    { key: "data_flows", title: t("diff.aggFlows"), section: aggregate.data_flows },
    { key: "trust_boundaries", title: t("diff.aggTrust"), section: aggregate.trust_boundaries },
    { key: "threats", title: t("diff.aggThreats"), section: aggregate.threats },
    { key: "mitigations", title: t("diff.aggMitigations"), section: aggregate.mitigations },
  ];
  const changed = sections.filter((s) => sectionHasChanges(s.section));
  return (
    <Card className="space-y-3 p-5" variant="glass">
      <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.changesBySection")}</h2>
      {changed.length === 0 ? (
        <p className="text-sm text-otm-text-muted">{t("diff.noSectionChanges")}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {changed.map((s) => (
            <AggregateBlock key={s.key} title={s.title} section={s.section} />
          ))}
        </div>
      )}
    </Card>
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
  const { t } = useTranslation();
  return (
    <Card className="space-y-4 p-5" variant="glass">
      <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.summary")}</h2>
      <p className="text-base font-medium leading-relaxed text-otm-text">{summary.headline}</p>
      {/*
        `summary.headline` and `structural.summary_line` are separate fields that the server
        very often fills with the same sentence, which printed the identical line twice — once
        bold, once muted — in both the no-change and the with-change case. Show the second
        only when it says something the first did not.
      */}
      {structuralLine && structuralLine !== summary.headline ? (
        <p className="text-sm text-otm-text-muted">{structuralLine}</p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {summary.has_structural_changes ? <Badge tone="accent">{t("diff.structural")}</Badge> : null}
        {summary.has_analysis_changes ? <Badge tone="accent">{t("diff.analysis")}</Badge> : null}
        {summary.methodology_in_model_changed ? <Badge tone="warn">{t("diff.methodologyModel")}</Badge> : null}
      </div>
      {runAnalysis && typeof maxRev === "number" ? (
        <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/70 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-otm-text-subtle">{t("diff.maxLi")}</p>
          <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-otm-text">{maxRev}</p>
          {typeof maxBase === "number" ? (
            <p className="mt-0.5 text-xs text-otm-text-muted">{t("diff.baseline", { value: maxBase })}</p>
          ) : null}
          <RiskScoreBar score={maxRev} className="mt-3" caption={t("diff.riskCaption")} />
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
  const { t } = useTranslation();
  const hasDelta =
    runAnalysis &&
    (typeof rd.analysis_max_score_delta === "number" ||
      (rd.heuristic_increased_ids?.length ?? 0) > 0 ||
      (rd.heuristic_decreased_ids?.length ?? 0) > 0);
  if (!hasDelta) return null;
  let deltaVal = "";
  if (typeof rd.analysis_max_score_delta === "number") {
    const n = rd.analysis_max_score_delta;
    const sign = n >= 0 ? "+" : "";
    deltaVal = `${sign}${n.toFixed(2)}`;
  }
  return (
    <Card className="space-y-3 p-5" variant="elevated">
      <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.riskDeltas")}</h2>
      {typeof rd.analysis_max_score_delta === "number" ? (
        <p className="text-sm text-otm-text-muted">
          <Trans
            i18nKey="diff.deltaScore"
            values={{
              delta: deltaVal,
              before: String(rd.analysis_max_score_baseline ?? "—"),
              after: String(rd.analysis_max_score_revised ?? "—"),
            }}
            components={{ strong: <strong className="text-otm-text" /> }}
          />
        </p>
      ) : null}
      {(rd.heuristic_increased_ids?.length ?? 0) > 0 ? (
        <p className="text-xs text-red-200">
          {t("diff.scoresUp", { ids: previewIds(rd.heuristic_increased_ids ?? []) })}
        </p>
      ) : null}
      {(rd.heuristic_decreased_ids?.length ?? 0) > 0 ? (
        <p className="text-xs text-emerald-200">
          {t("diff.scoresDown", { ids: previewIds(rd.heuristic_decreased_ids ?? []) })}
        </p>
      ) : null}
    </Card>
  );
}

function SemanticDiffSectionsBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const { t } = useTranslation();
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
          <p className="font-semibold text-otm-text">{t("diff.structuralCounts")}</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {scs.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {imp.length ? (
        <div className="rounded-otm-md border border-emerald-500/20 bg-emerald-950/15 p-3 text-xs text-otm-text-muted">
          <p className="font-semibold text-emerald-900 dark:text-emerald-100">{t("diff.improved")}</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {imp.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {wor.length ? (
        <div className="rounded-otm-md border border-amber-500/20 bg-amber-950/15 p-3 text-xs text-otm-text-muted">
          <p className="font-semibold text-amber-900 dark:text-amber-100">{t("diff.worsened")}</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {wor.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {risk.length ? (
        <div className="rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 text-xs text-otm-text-muted sm:col-span-3 lg:col-span-1">
          <p className="font-semibold text-otm-text">{t("diff.riskImpact")}</p>
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

function InterpretationLinksBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const { t } = useTranslation();
  const links = meta.semantic_interpretation_links ?? [];
  if (!links.length) return null;
  return (
    <div data-testid="diff-interpretation-links">
      <Card className="space-y-2 p-4" variant="glass">
        <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.interpretationLinks")}</h2>
        <p className="text-xs text-otm-text-muted">
          <Trans
            i18nKey="diff.interpretationNote"
            components={{
              strong: <strong />,
              0: <code className="text-otm-accent" />,
              1: <code className="text-otm-accent" />,
              2: <code className="text-otm-accent" />,
            }}
          />
        </p>
        <ul className="list-inside list-disc space-y-1.5 text-xs text-otm-text-muted">
          {links.slice(0, 10).map((l) => (
            <li key={`${l.structural_ref}-${l.related_section}-${l.summary.slice(0, 24)}`}>
              <span className="font-mono text-otm-accent">{l.structural_ref}</span> →{" "}
              <span className="text-otm-text">{l.related_section}</span>
              {l.link_kind ? (
                <span className="text-otm-text-subtle">
                  {" "}
                  · {l.link_kind}
                  {l.inference_strength ? ` (${l.inference_strength})` : ""}
                </span>
              ) : null}
              : {l.summary}
              {l.anchoring_rationale ? (
                <span className="mt-0.5 block italic text-otm-text-subtle">
                  {l.anchoring_rationale}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function StructuralRefsBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const { t } = useTranslation();
  const refs = meta.semantic_structural_refs ?? [];
  if (!refs.length) return null;
  return (
    <div data-testid="diff-structural-refs">
      <Card className="space-y-2 p-4" variant="glass">
        <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.structureInterpretation")}</h2>
        <p className="text-xs text-otm-text-muted">{t("diff.structureNote")}</p>
        <ul className="list-inside list-disc space-y-1.5 text-xs text-otm-text-muted">
          {refs.slice(0, 12).map((r) => (
            <li key={r.ref}>
              <span className="font-mono text-otm-accent">{r.ref}</span> · {r.entity_kind}{" "}
              <span className="text-otm-text">{r.entity_id}</span>
              {r.change_category ? (
                <span className="text-otm-text-subtle"> · {r.change_category}</span>
              ) : null}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function SemanticInsightsBlock({ meta }: Readonly<{ meta: ComparisonMeta }>) {
  const { t } = useTranslation();
  const raw = meta.semantic_insights;
  const insights: string[] = Array.isArray(raw) ? raw.filter((item): item is string => typeof item === "string") : [];
  const ver = typeof meta.semantic_insights_version === "string" ? meta.semantic_insights_version : "";
  const disc = typeof meta.interpretation_disclaimer === "string" ? meta.interpretation_disclaimer : "";
  const hasSections =
    meta.semantic_diff_sections != null && typeof meta.semantic_diff_sections === "object";
  if (insights.length === 0 && !hasSections) return null;
  return (
    <div data-testid="diff-semantic-panel">
      <Card className="space-y-2 p-4" variant="elevated">
        <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.semanticDiff")}</h2>
        {ver ? (
          <p className="text-[10px] uppercase tracking-wide text-otm-text-subtle">{t("diff.version", { ver })}</p>
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
  const { t } = useTranslation();
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
          <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.keyInsights")}</h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-otm-text-muted">
            {result.key_insights.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      {result.explanations && result.explanations.length > 0 ? (
        <details className="rounded-otm-lg border border-otm-border bg-otm-surface-2 p-4 text-sm text-otm-text">
          <summary className="cursor-pointer font-semibold">{t("diff.whyStructured")}</summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-otm-text-muted">
            {result.explanations.slice(0, 6).map((e) => (
              <li key={e.id}>
                <span className="font-medium text-otm-text">{e.subject}:</span> {e.message}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <AggregateSectionsCard aggregate={result.aggregate} />

      <DiffRiskDeltaCard rd={rd} runAnalysis={runAnalysis} />

      <SemanticInsightsBlock meta={result.meta as ComparisonMeta} />

      <StructuralRefsBlock meta={result.meta as ComparisonMeta} />

      <InterpretationLinksBlock meta={result.meta as ComparisonMeta} />

      <Card className="space-y-2 p-4" variant="glass">
        <h2 className="font-display text-sm font-semibold text-otm-text">{t("diff.fullJson")}</h2>
        <pre className="max-h-[360px] overflow-auto rounded-otm-md bg-otm-green-950 p-3 text-xs text-otm-mint-300">
          {JSON.stringify(result, null, 2)}
        </pre>
      </Card>
    </div>
  );
}

export function DiffPage() {
  const { t } = useTranslation();
  const { document: baseline } = useSession();
  const toast = useToast();
  const [revisedText, setRevisedText] = useState("");
  const [runAnalysis, setRunAnalysis] = useState(false);
  const [packId, setPackId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ThreatModelComparisonResult | null>(null);

  const onFile = useCallback(
    (file: File | null) => {
      if (!file) return;
      const r = new FileReader();
      r.onload = () => {
        setRevisedText(typeof r.result === "string" ? r.result : "");
        setResult(null);
        setError(null);
      };
      // Sem `onerror` uma leitura falhada (ficheiro removido, permissões, disco) não dizia
      // nada: a área de texto ficava vazia e o utilizador não sabia se tinha escolhido mal
      // o ficheiro ou se a página estava avariada.
      r.onerror = () => {
        const msg = t("diff.readFail");
        setError(msg);
        toast.error(msg);
      };
      r.readAsText(file, "UTF-8");
    },
    [t, toast],
  );

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
      const msg = e instanceof Error ? e.message : t("diff.parseFail");
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
      toast.success(t("diff.toastOk"));
    } catch (e) {
      const msg = apiErrorMessage(e, t, "diff.toastFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={t("diff.eyebrow")}
        title={t("diff.title")}
        description={
          <Trans
            i18nKey="diff.description"
            components={{
              strong: <strong className="text-otm-text" />,
              0: <code className="rounded bg-otm-surface-3 px-1 text-xs text-otm-accent" />,
            }}
          />
        }
      />

      <div className="space-y-3 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <HelpCallout title={t("diff.helpTitle")}>
          <Trans
            i18nKey="diff.helpBody"
            components={{ strong: <strong className="text-otm-text" /> }}
          />
        </HelpCallout>
      </div>

      <Card className="space-y-3 p-4" variant="elevated">
        <div>
          <Label htmlFor="revised-json">{t("diff.revisionJson")}</Label>
          <textarea
            id="revised-json"
            className="mt-1 min-h-[180px] w-full rounded-otm-md border border-otm-border-control bg-otm-surface-1 px-3 py-2 font-mono text-xs text-otm-text placeholder:text-otm-text-subtle focus:border-otm-mint-400/50 focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)]"
            value={revisedText}
            onChange={(ev) => setRevisedText(ev.target.value)}
            placeholder={t("diff.revisionPlaceholder")}
          />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-otm-text-muted">
            <Checkbox checked={runAnalysis} onChange={(e) => setRunAnalysis(e.target.checked)} />
            {t("diff.includeAnalysis")}
          </label>
        </div>
        {runAnalysis ? (
          <div>
            <Label htmlFor="pack-id">{t("diff.packOptional")}</Label>
            <Input
              id="pack-id"
              className="mt-1 max-w-md font-mono text-sm"
              value={packId}
              onChange={(e) => setPackId(e.target.value)}
              placeholder={t("diff.packPlaceholder")}
            />
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          {/* Rótulo sr-only como em ImportPage: sem ele o leitor de ecrã anuncia um botão
              sem nome num dos dois caminhos para fornecer o modelo revisto. */}
          <Label htmlFor="revised-file" className="sr-only">
            {t("diff.revisionFileLabel")}
          </Label>
          <input
            id="revised-file"
            type="file"
            accept=".json,application/json"
            className="text-sm text-otm-text-muted file:mr-2"
            onChange={(ev) => onFile(ev.target.files?.[0] ?? null)}
          />
          <Button type="button" onClick={() => void runDiff()} disabled={loading || !revisedText.trim()}>
            {loading ? t("diff.comparing") : t("diff.compare")}
          </Button>
        </div>
      </Card>

      {error ? <Alert variant="error">{error}</Alert> : null}

      {result ? <ComparisonResultPanel result={result} runAnalysis={runAnalysis} /> : null}
    </div>
  );
}
