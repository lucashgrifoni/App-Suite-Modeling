import { useMemo, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import {
  resolveExportArtifactLocale,
  type ExportArtifactLocale,
} from "../i18n/exportArtifactLocale";
import { Navigate } from "react-router";
import { exportArtifacts, fetchPremiumReport, type PremiumReportLevel } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Label } from "../components/ui/Label";
import { Checkbox } from "../components/ui/Checkbox";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { WorkflowGuide } from "../components/onboarding/WorkflowGuide";
import { ContextHint } from "../components/onboarding/ContextHint";
import { useAnalysisHistory } from "../context/AnalysisHistoryContext";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { downloadPdfBlob, generateReportPdfBlob } from "../lib/generateReportPdf";
import { extFor, mimeFor } from "../utils/exportArtifactHelpers";
import type { ExportFormat } from "../types/api";

const FORMAT_DEFS: ReadonlyArray<{
  id: ExportFormat;
  labelKey: string;
  hintKey: string;
}> = [
  { id: "document_json", labelKey: "export.fmtJson", hintKey: "export.fmtJsonHint" },
  { id: "document_markdown", labelKey: "export.fmtMd", hintKey: "export.fmtMdHint" },
  { id: "flowchart_mermaid", labelKey: "export.fmtMermaid", hintKey: "export.fmtMermaidHint" },
  { id: "analysis_json", labelKey: "export.fmtAnalysisJson", hintKey: "export.fmtAnalysisJsonHint" },
  { id: "analysis_markdown", labelKey: "export.fmtAnalysisMd", hintKey: "export.fmtAnalysisMdHint" },
  { id: "bundle_json", labelKey: "export.fmtBundle", hintKey: "export.fmtBundleHint" },
];

function downloadArtifact(name: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = globalThis.document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

type ArtifactLocaleChoice = "ui" | ExportArtifactLocale;

export function ExportPage() {
  const { t, i18n } = useTranslation();
  const { document: otmDoc, analysis } = useSession();
  const { appendSnapshot } = useAnalysisHistory();
  const toast = useToast();
  const [selected, setSelected] = useState<Set<ExportFormat>>(
    () => new Set(["document_markdown", "analysis_markdown"]),
  );
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [premiumLoading, setPremiumLoading] = useState(false);
  const [premiumLevel, setPremiumLevel] = useState<PremiumReportLevel>("standard");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, string> | null>(null);
  const [artifactLocaleChoice, setArtifactLocaleChoice] = useState<ArtifactLocaleChoice>("ui");

  const resolvedArtifactLocale = (): ExportArtifactLocale =>
    resolveExportArtifactLocale(
      artifactLocaleChoice === "ui" ? undefined : artifactLocaleChoice,
      i18n.language,
    );

  const formats = useMemo(
    () => FORMAT_DEFS.map((f) => ({ ...f, label: t(f.labelKey), hint: t(f.hintKey) })),
    [t],
  );

  if (!otmDoc) return <Navigate to="/" replace />;
  const model = otmDoc;

  function toggle(id: ExportFormat) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function runExport() {
    setError(null);
    setResult(null);
    if (selected.size === 0) {
      const msg = t("export.pickOne");
      setError(msg);
      toast.warning(msg);
      return;
    }
    setLoading(true);
    try {
      const needsAnalysis = [...selected].some((f) =>
        ["analysis_json", "analysis_markdown", "bundle_json"].includes(f),
      );
      const { artifacts } = await exportArtifacts({
        document: model,
        formats: [...selected],
        analysis: needsAnalysis ? analysis : null,
        locale: resolvedArtifactLocale(),
      });
      setResult(artifacts);
      appendSnapshot("export");
      toast.success(t("export.toastReady"));
    } catch (e) {
      const msg = apiErrorMessage(e, t, "export.toastFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  async function runPdf() {
    setError(null);
    setPdfLoading(true);
    try {
      await new Promise<void>((r) => {
        queueMicrotask(r);
      });
      const blob = await generateReportPdfBlob(model, analysis, {
        locale: resolvedArtifactLocale(),
      });
      const safe = model.metadata.title.replaceAll(/[^\w-]+/g, "_").slice(0, 40);
      downloadPdfBlob(blob, `otm-report-${safe}.pdf`);
      appendSnapshot("export");
      toast.success(t("export.toastPdf"));
    } catch {
      const msg = t("export.toastPdfFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setPdfLoading(false);
    }
  }

  async function runPremium(kind: "markdown" | "pdf") {
    setError(null);
    setPremiumLoading(true);
    try {
      const { blob, filename } = await fetchPremiumReport({
        document: model,
        analysis,
        level: premiumLevel,
        outputFormat: kind,
        locale: resolvedArtifactLocale(),
      });
      downloadPdfBlob(blob, filename);
      appendSnapshot("export");
      toast.success(kind === "pdf" ? t("export.toastPremiumPdf") : t("export.toastPremiumMd"));
    } catch (e) {
      const msg = apiErrorMessage(e, t, "export.toastPremiumFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setPremiumLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader eyebrow={t("export.eyebrow")} title={t("export.title")} description={t("export.description")} />

      <div className="space-y-2 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <ContextHint>
          <Trans
            i18nKey="export.contextHint"
            components={{ strong: <strong className="text-otm-text-muted" /> }}
          />
        </ContextHint>
      </div>

      <Card title={t("export.formatsTitle")} subtitle={t("export.formatsSubtitle")} variant="glass">
        <ul className="space-y-3">
          {formats.map((f) => (
            <li
              key={f.id}
              className="flex items-start gap-3 rounded-otm-md border border-transparent px-2 py-2 transition hover:border-otm-border hover:bg-otm-surface-1/60"
            >
              <Checkbox
                id={f.id}
                checked={selected.has(f.id)}
                onChange={() => toggle(f.id)}
                className="mt-1"
              />
              <div>
                <Label htmlFor={f.id} className="!mb-0 cursor-pointer font-medium text-otm-text">
                  {f.label}
                </Label>
                <p className="text-xs text-otm-text-muted">{f.hint}</p>
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-3 max-w-xs">
          <Label htmlFor="artifact-locale">{t("export.artifactLanguage")}</Label>
          <select
            id="artifact-locale"
            data-testid="export-artifact-locale"
            value={artifactLocaleChoice}
            onChange={(e) => setArtifactLocaleChoice(e.target.value as ArtifactLocaleChoice)}
            className="mt-1 flex h-10 w-full rounded-otm-md border border-otm-border bg-otm-surface px-3 text-sm text-otm-text shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-otm-accent"
          >
            <option value="ui">{t("export.artifactLangUi")}</option>
            <option value="pt-BR">{t("export.artifactLangPtBR")}</option>
            <option value="en">{t("export.artifactLangEn")}</option>
          </select>
        </div>
        <Button className="mt-4" onClick={() => void runExport()} disabled={loading || pdfLoading || premiumLoading}>
          {loading ? t("export.generating") : t("export.generateFiles")}
        </Button>
      </Card>

      <Card title={t("export.premiumTitle")} subtitle={t("export.premiumSubtitle")} variant="elevated">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="premium-level" className="text-xs text-otm-text-muted">
              {t("export.level")}
            </Label>
            <select
              id="premium-level"
              className="mt-1 block rounded-otm-md border border-otm-border bg-otm-surface-1 px-3 py-2 text-sm text-otm-text"
              value={premiumLevel}
              onChange={(e) => setPremiumLevel(e.target.value as PremiumReportLevel)}
            >
              <option value="executive">{t("export.optExecutive")}</option>
              <option value="standard">{t("export.optStandard")}</option>
              <option value="deep">{t("export.optDeep")}</option>
            </select>
          </div>
          <Button
            variant="secondary"
            data-testid="export-premium-md"
            onClick={() => void runPremium("markdown")}
            disabled={premiumLoading || loading || pdfLoading}
          >
            {premiumLoading ? t("export.generating") : t("export.premiumMd")}
          </Button>
          <Button
            data-testid="export-premium-pdf"
            onClick={() => void runPremium("pdf")}
            disabled={premiumLoading || loading || pdfLoading}
          >
            {premiumLoading ? t("export.generating") : t("export.premiumPdf")}
          </Button>
        </div>
        <p className="mt-3 text-xs text-otm-text-muted">{t("export.premiumNote")}</p>
      </Card>

      <Card title={t("export.pdfCardTitle")} subtitle={t("export.pdfCardSubtitle")} variant="elevated">
        <p className="text-sm text-otm-text-muted">{t("export.pdfCardBody")}</p>
        <Button
          className="mt-4"
          data-testid="export-pdf"
          onClick={() => void runPdf()}
          disabled={pdfLoading || loading || premiumLoading}
        >
          {pdfLoading ? t("export.generatingPdf") : t("export.generatePdf")}
        </Button>
      </Card>

      {error && <Alert>{error}</Alert>}

      {result && (
        <div data-testid="export-download-section">
          <Card title={t("export.downloadTitle")} subtitle={t("export.downloadSubtitle")} variant="elevated">
            <ul className="space-y-2">
              {Object.entries(result).map(([key, text]) => (
                <li key={key} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-mono text-otm-accent">{key}</span>
                  <Button
                    variant="secondary"
                    className="!py-1.5 !text-xs"
                    onClick={() =>
                      downloadArtifact(
                        `otm-export-${key}.${extFor(key)}`,
                        text,
                        mimeFor(key),
                      )
                    }
                  >
                    {t("export.download")}
                  </Button>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-otm-text-muted">{t("export.copyPreview")}</p>
            {Object.entries(result).map(([key, text]) => (
              <details key={`d-${key}`} className="mt-2 rounded-otm-md border border-otm-border bg-otm-surface-1/50 p-2">
                <summary className="cursor-pointer text-sm font-medium text-otm-text">
                  {key}
                </summary>
                <pre className="mt-2 max-h-48 overflow-auto rounded-otm-md bg-otm-green-950 p-3 text-xs text-otm-mint-300">
                  {text.slice(0, 8000)}
                  {text.length > 8000 ? "\n…" : ""}
                </pre>
              </details>
            ))}
          </Card>
        </div>
      )}
    </div>
  );
}
