import { useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { resolveExportArtifactLocale } from "../i18n/exportArtifactLocale";
import { useNavigate } from "react-router";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { PageHeader } from "../components/patterns/PageHeader";
import { EmptyState } from "../components/patterns/EmptyState";
import { useAnalysisHistory } from "../context/AnalysisHistoryContext";
import { useToast } from "../context/ToastContext";
import { fetchRiskReport, type RiskReportFormat } from "../api/otmApi";
import { apiErrorMessage } from "../api/apiErrorMessage";
import { downloadBlob } from "../utils/exportArtifactHelpers";
import type { AnalysisHistoryEntry } from "../types/analysisHistory";

function countActiveThreats(entry: AnalysisHistoryEntry): number {
  const list = entry.analysis?.heuristic_threats;
  if (!list) return 0;
  return list.filter((t) => !t.skipped_as_duplicate).length;
}

function compactSnapshotPreview(entry: AnalysisHistoryEntry): string {
  return JSON.stringify(
    {
      title: entry.document.metadata.title,
      system_type: entry.document.model.system_type,
      methodology: entry.document.model.methodology,
      components: entry.document.components.length,
      data_flows: entry.document.data_flows.length,
      trust_boundaries: entry.document.trust_boundaries?.length ?? 0,
      analysis_attached: Boolean(entry.analysis),
      heuristic_threats_active: countActiveThreats(entry),
      max_risk_score: entry.analysis?.summary?.max_risk_score ?? null,
    },
    null,
    2,
  );
}

function HistoryCard({
  entry,
  reportPending,
  onRestore,
  onExport,
  onReport,
  onRemove,
}: Readonly<{
  entry: AnalysisHistoryEntry;
  reportPending: { id: string; format: RiskReportFormat } | null;
  onRestore: (id: string) => void;
  onExport: (id: string) => void;
  onReport: (id: string, format: RiskReportFormat) => void;
  onRemove: (id: string) => void;
}>) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language.startsWith("pt") ? "pt-BR" : "en-US";
  let whenStr: string;
  try {
    whenStr = new Date(entry.createdAt).toLocaleString(locale, {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    whenStr = String(entry.createdAt);
  }
  const triggerLabel =
    entry.trigger === "analysis" ? t("history.triggerAnalysis") : t("history.triggerExport");
  return (
    <Card variant="default" title={entry.title} subtitle={`${whenStr} · ${triggerLabel}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm text-otm-text-muted">
        <Badge tone="neutral">{entry.systemType}</Badge>
        <span>
          {t("history.maxLi")} {entry.maxScore ?? "—"}
        </span>
      </div>
      <p className="mt-2 text-xs text-otm-text-subtle">
        {t("history.summaryLine", { title: entry.title, score: entry.maxScore ?? "—" })}
      </p>
      <div
        className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-otm-text-muted"
        data-testid="history-snapshot-stats"
      >
        <span>
          {t("history.components")} {entry.document.components.length}
        </span>
        <span>
          {t("history.flows")} {entry.document.data_flows.length}
        </span>
        <span>
          {t("history.heuristicThreats")} {countActiveThreats(entry)}
        </span>
      </div>
      <details className="mt-3 rounded-otm-md border border-otm-border bg-otm-surface-1/50 p-2">
        <summary className="cursor-pointer text-xs font-medium text-otm-text">
          {t("history.snapshotSummary")}
        </summary>
        <pre className="mt-2 max-h-40 overflow-auto rounded-otm-md bg-otm-green-950/80 p-2 font-mono text-[11px] text-otm-mint-300">
          {compactSnapshotPreview(entry)}
        </pre>
      </details>
      <p className="mt-4 text-xs text-otm-text-muted">{t("work.restoreEffect")}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          className="!py-1.5 !text-xs"
          onClick={() => onRestore(entry.id)}
        >
          {t("history.restore")}
        </Button>
        <Button
          type="button"
          variant="secondary"
          className="!py-1.5 !text-xs"
          onClick={() => onExport(entry.id)}
        >
          {t("history.goExport")}
        </Button>
        {(["pdf", "markdown"] as const).map((format) => (
          <Button
            type="button"
            key={format}
            variant="ghost"
            className="!py-1.5 !text-xs"
            disabled={reportPending !== null}
            onClick={() => onReport(entry.id, format)}
          >
            {reportPending?.id === entry.id && reportPending.format === format
              ? t("export.generating")
              : t(format === "pdf" ? "history.pdfSnapshot" : "history.markdownSnapshot")}
          </Button>
        ))}
        <Button
          type="button"
          variant="ghost"
          className="!py-1.5 !text-xs"
          onClick={() => onRemove(entry.id)}
        >
          {t("history.remove")}
        </Button>
      </div>
    </Card>
  );
}

export function HistoryPage() {
  const { t, i18n } = useTranslation();
  const { entries, restore, remove } = useAnalysisHistory();
  const toast = useToast();
  const navigate = useNavigate();
  const [reportPending, setReportPending] = useState<{ id: string; format: RiskReportFormat } | null>(null);
  const reportRunning = useRef(false);

  const [selectedId, setSelectedId] = useState("");
  const selected = entries.find((entry) => entry.id === selectedId) ?? entries[0];
  const locale = i18n.language.startsWith("pt") ? "pt-BR" : "en-US";

  function confirmRestore(id: string) {
    if (!globalThis.confirm(t("history.confirmRestore"))) {
      return;
    }
    restore(id);
    toast.success(t("history.toastRestored"));
    navigate("/analysis");
  }

  function handleExport(id: string) {
    if (!globalThis.confirm(t("history.confirmExport"))) {
      return;
    }
    restore(id);
    toast.info(t("history.toastSession"));
    navigate("/export");
  }

  async function handleReport(id: string, format: RiskReportFormat) {
    const e = entries.find((x) => x.id === id);
    if (!e) return;
    // The rendered buttons are disabled while one render is in flight; this closes the gap
    // for a double-click delivered before that state reaches the DOM.
    if (reportRunning.current) return;
    reportRunning.current = true;
    setReportPending({ id, format });
    try {
      const { blob, filename } = await fetchRiskReport({
        document: e.document,
        analysis: e.analysis,
        outputFormat: format,
        locale: resolveExportArtifactLocale(undefined, i18n.language),
        snapshotDate: e.createdAt,
      });
      downloadBlob(blob, filename);
      toast.success(t("history.reportReady"));
    } catch (error) {
      toast.error(apiErrorMessage(error, t, "export.reportUnavailable"));
    } finally {
      reportRunning.current = false;
      setReportPending(null);
    }
  }

  return (
    <div className="work-page">
      <PageHeader
        eyebrow={t("history.eyebrow")}
        title={t("history.title")}
        description={t("history.description")}
      />

      {entries.length === 0 ? (
        <EmptyState
          title={t("history.emptyTitle")}
          description={
            <Trans
              i18nKey="history.emptyDesc"
              components={{ strong: <strong className="text-otm-text" /> }}
            />
          }
        />
      ) : (
        <div className="work-split">
          <Card title={t("work.savedRecords")}>
            <ul data-testid="history-list">
              {entries.map((entry) => (
                <li key={entry.id}>
                  <button
                    type="button"
                    className="work-select-row grid-cols-[minmax(0,1.4fr)_minmax(70px,1fr)_auto]"
                    aria-pressed={entry.id === selected.id}
                    onClick={() => setSelectedId(entry.id)}
                  >
                    <span>
                      <b>
                        {t(
                          entry.trigger === "analysis"
                            ? "history.triggerAnalysis"
                            : "history.triggerExport",
                        )}
                      </b>
                      <small>{entry.title}</small>
                    </span>
                    <small>
                      {new Date(entry.createdAt).toLocaleString(locale, {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </small>
                    <span className="work-score" title={t("metrics.maxLi")}>
                      {entry.maxScore ?? "—"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          <aside>
            <HistoryCard
              key={selected.id}
              entry={selected}
              reportPending={reportPending}
              onRestore={confirmRestore}
              onExport={handleExport}
              onReport={handleReport}
              onRemove={(id) => {
                remove(id);
                toast.info(t("history.toastRemoved"));
              }}
            />
          </aside>
        </div>
      )}
    </div>
  );
}
