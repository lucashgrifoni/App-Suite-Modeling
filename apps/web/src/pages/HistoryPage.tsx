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
import { downloadPdfBlob, generateReportPdfBlob } from "../lib/generateReportPdf";
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
  activeId,
  pdfPendingId,
  onRestore,
  onExport,
  onPdf,
  onRemove,
}: Readonly<{
  entry: AnalysisHistoryEntry;
  activeId: string | null;
  /** The snapshot currently being rendered to PDF, if any. */
  pdfPendingId: string | null;
  onRestore: (id: string) => void;
  onExport: (id: string) => void;
  onPdf: (id: string) => void;
  onRemove: (id: string) => void;
}>) {
  const { t, i18n } = useTranslation();
  const isActive = activeId === entry.id;
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
    <Card
      variant={isActive ? "elevated" : "glass"}
      className={isActive ? "ring-2 ring-[color:var(--otm-ring)]" : ""}
      title={entry.title}
      subtitle={`${whenStr} · ${triggerLabel}`}
    >
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
      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="button" variant="secondary" className="!py-1.5 !text-xs" onClick={() => onRestore(entry.id)}>
          {t("history.restore")}
        </Button>
        <Button type="button" variant="secondary" className="!py-1.5 !text-xs" onClick={() => onExport(entry.id)}>
          {t("history.goExport")}
        </Button>
        {/*
          Client-side jsPDF rendering takes seconds on a real model, and this button used to
          give no sign it had started: no disabled state, no label change. Three clicks —
          the natural response to a control that appears to do nothing — started three full
          renders and dropped three identical files into the Downloads folder. Every PDF
          button on the export page already guards this way.
        */}
        <Button
          type="button"
          variant="ghost"
          className="!py-1.5 !text-xs"
          disabled={pdfPendingId !== null}
          onClick={() => {
            onPdf(entry.id);
          }}
        >
          {pdfPendingId === entry.id ? t("history.pdfSnapshotLoading") : t("history.pdfSnapshot")}
        </Button>
        <Button type="button" variant="ghost" className="!py-1.5 !text-xs" onClick={() => onRemove(entry.id)}>
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
  const [pdfPendingId, setPdfPendingId] = useState<string | null>(null);
  const pdfRunning = useRef(false);

  /** Destaque do snapshot mais recente (primeiro da lista). */
  const newestId = entries[0]?.id ?? null;

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

  async function handlePdf(id: string) {
    const e = entries.find((x) => x.id === id);
    if (!e) return;
    // The rendered buttons are disabled while one render is in flight; this closes the gap
    // for a double-click delivered before that state reaches the DOM.
    if (pdfRunning.current) return;
    pdfRunning.current = true;
    setPdfPendingId(id);
    try {
      const blob = await generateReportPdfBlob(e.document, e.analysis, {
        locale: resolveExportArtifactLocale(undefined, i18n.language),
      });
      const safe = e.title.replaceAll(/[^\w-]+/g, "_").slice(0, 40);
      downloadPdfBlob(blob, `otm-report-${safe}-${e.createdAt}.pdf`);
      toast.success(t("history.toastPdfOk"));
    } catch {
      toast.error(t("history.toastPdfFail"));
    } finally {
      pdfRunning.current = false;
      setPdfPendingId(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader eyebrow={t("history.eyebrow")} title={t("history.title")} description={t("history.description")} />

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
        <ul className="space-y-4" data-testid="history-list">
          {entries.map((e) => (
            <li key={e.id}>
              <HistoryCard
                entry={e}
                activeId={newestId}
                pdfPendingId={pdfPendingId}
                onRestore={confirmRestore}
                onExport={handleExport}
                onPdf={handlePdf}
                onRemove={(id) => {
                  remove(id);
                  toast.info(t("history.toastRemoved"));
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
