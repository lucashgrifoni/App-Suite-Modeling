import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  resolveExportArtifactLocale,
  type ExportArtifactLocale,
} from "../i18n/exportArtifactLocale";
import { Navigate } from "react-router";
import { exportArtifacts, fetchRiskReport, type RiskReportFormat } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Label } from "../components/ui/Label";
import { Checkbox } from "../components/ui/Checkbox";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/patterns/PageHeader";
import { ModelSummary } from "../components/patterns/ModelSummary";
import { useAnalysisHistory } from "../context/AnalysisHistoryContext";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { downloadBlob, extFor, mimeFor } from "../utils/exportArtifactHelpers";
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
  const [reportLoading, setReportLoading] = useState<RiskReportFormat | null>(null);
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
      const stored = appendSnapshot("export");
      toast.success(t("export.toastReady"));
      if (stored === "failed") toast.warning(t("history.toastStorageFull"));
      // `"evicted"` era calculado e deitado fora: snapshots antigos desapareciam para
      // abrir espaço a este, debaixo de um toast de sucesso sem ressalva, e o "máximo 20"
      // que a página de Histórico anuncia deixava de se verificar sem ninguém saber.
      else if (stored === "evicted") toast.warning(t("history.toastStorageEvicted"));
    } catch (e) {
      const msg = apiErrorMessage(e, t, "export.toastFail");
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  async function runReport(kind: RiskReportFormat) {
    setError(null);
    setReportLoading(kind);
    try {
      const { blob, filename } = await fetchRiskReport({
        document: model,
        analysis,
        outputFormat: kind,
        locale: resolvedArtifactLocale(),
      });
      downloadBlob(blob, filename);
      const stored = appendSnapshot("export");
      toast.success(t("export.reportReady"));
      if (stored === "failed") toast.warning(t("history.toastStorageFull"));
      // `"evicted"` era calculado e deitado fora: snapshots antigos desapareciam para
      // abrir espaço a este, debaixo de um toast de sucesso sem ressalva, e o "máximo 20"
      // que a página de Histórico anuncia deixava de se verificar sem ninguém saber.
      else if (stored === "evicted") toast.warning(t("history.toastStorageEvicted"));
    } catch (e) {
      const msg = apiErrorMessage(e, t, "export.reportUnavailable");
      setError(msg);
      toast.error(msg);
    } finally {
      setReportLoading(null);
    }
  }

  return (
    <div className="work-page">
      <PageHeader
        eyebrow={t("export.eyebrow")}
        title={t("export.title")}
        description={t("export.description")}
      />

      <Card title={t("export.reportTitle")} subtitle={t("export.reportSubtitle")} variant="elevated">
        <div className="max-w-xs">
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
        <div className="mt-3 flex flex-wrap gap-3">
          <Button
            data-testid="export-pdf"
            onClick={() => void runReport("pdf")}
            disabled={loading || reportLoading !== null}
          >
            {reportLoading === "pdf" ? t("export.generating") : t("export.reportPdf")}
          </Button>
          <Button
            variant="secondary"
            data-testid="export-report-md"
            onClick={() => void runReport("markdown")}
            disabled={loading || reportLoading !== null}
          >
            {reportLoading === "markdown" ? t("export.generating") : t("export.reportMarkdown")}
          </Button>
        </div>
      </Card>
      <div className="work-split">
        <Card title={t("export.formatsTitle")} subtitle={t("export.formatsSubtitle")} variant="glass">
          <ul className="grid gap-2 sm:grid-cols-2">
            {formats.map((f) => (
              <li
                key={f.id}
                className="flex items-start gap-3 rounded-otm-md border border-otm-border-strong px-3 py-3 has-[:checked]:bg-otm-primary-muted transition hover:border-otm-border hover:bg-otm-surface-1/60"
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
          <Button
            className="mt-4"
            onClick={() => void runExport()}
            disabled={loading || reportLoading !== null}
          >
            {loading ? t("export.generating") : t("export.generateFiles")}
          </Button>
        </Card>

        <aside className="grid gap-4">
          {result && (
            <div data-testid="export-download-section">
              <Card
                title={t("export.downloadTitle")}
                subtitle={t("export.downloadSubtitle")}
                variant="elevated"
              >
                <ul className="space-y-2">
                  {Object.entries(result).map(([key, text]) => (
                    <li key={key} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span className="font-mono text-otm-accent">{key}</span>
                      <Button
                        variant="secondary"
                        className="!py-1.5 !text-xs"
                        onClick={() =>
                          downloadBlob(new Blob([text], { type: mimeFor(key) }), `otm-export-${key}.${extFor(key)}`)
                        }
                      >
                        {t("export.download")}
                      </Button>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-otm-text-muted">{t("export.copyPreview")}</p>
                {Object.entries(result).map(([key, text]) => (
                  <details
                    key={`d-${key}`}
                    className="mt-2 rounded-otm-md border border-otm-border bg-otm-surface-1/50 p-2"
                  >
                    <summary className="cursor-pointer text-sm font-medium text-otm-text">{key}</summary>
                    <pre className="mt-2 max-h-48 overflow-auto rounded-otm-md bg-otm-green-950 p-3 text-xs text-otm-mint-300">
                      {text.slice(0, 8000)}
                      {text.length > 8000 ? "\n…" : ""}
                    </pre>
                  </details>
                ))}
              </Card>
            </div>
          )}
          <ModelSummary document={otmDoc} />
        </aside>
      </div>
      {error && <Alert>{error}</Alert>}
    </div>
  );
}
