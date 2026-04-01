import { useNavigate } from "react-router-dom";
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

function formatWhen(ts: number): string {
  try {
    return new Date(ts).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return String(ts);
  }
}

function HistoryCard({
  entry,
  activeId,
  onRestore,
  onExport,
  onPdf,
  onRemove,
}: Readonly<{
  entry: AnalysisHistoryEntry;
  activeId: string | null;
  onRestore: (id: string) => void;
  onExport: (id: string) => void;
  onPdf: (id: string) => void;
  onRemove: (id: string) => void;
}>) {
  const isActive = activeId === entry.id;
  return (
    <Card
      variant={isActive ? "elevated" : "glass"}
      className={isActive ? "ring-2 ring-[color:var(--otm-ring)]" : ""}
      title={entry.title}
      subtitle={`${formatWhen(entry.createdAt)} · ${entry.trigger === "analysis" ? "Análise" : "Exportação"}`}
    >
      <div className="flex flex-wrap items-center gap-2 text-sm text-otm-text-muted">
        <Badge tone="neutral">{entry.systemType}</Badge>
        <span>L×I máx.: {entry.maxScore ?? "—"}</span>
      </div>
      <p className="mt-2 text-xs text-otm-text-subtle">{entry.summaryLine}</p>
      <div
        className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-otm-text-muted"
        data-testid="history-snapshot-stats"
      >
        <span>Componentes: {entry.document.components.length}</span>
        <span>Fluxos: {entry.document.data_flows.length}</span>
        <span>Ameaças heurísticas: {countActiveThreats(entry)}</span>
      </div>
      <details className="mt-3 rounded-otm-md border border-otm-border bg-otm-surface-1/50 p-2">
        <summary className="cursor-pointer text-xs font-medium text-otm-text">
          Ver resumo do snapshot
        </summary>
        <pre className="mt-2 max-h-40 overflow-auto rounded-otm-md bg-otm-green-950/80 p-2 font-mono text-[11px] text-otm-mint-300">
          {compactSnapshotPreview(entry)}
        </pre>
      </details>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="button" variant="secondary" className="!py-1.5 !text-xs" onClick={() => onRestore(entry.id)}>
          Restaurar
        </Button>
        <Button type="button" variant="secondary" className="!py-1.5 !text-xs" onClick={() => onExport(entry.id)}>
          Ir para exportar
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="!py-1.5 !text-xs"
          onClick={() => void onPdf(entry.id)}
        >
          PDF deste snapshot
        </Button>
        <Button type="button" variant="ghost" className="!py-1.5 !text-xs" onClick={() => onRemove(entry.id)}>
          Remover
        </Button>
      </div>
    </Card>
  );
}

export function HistoryPage() {
  const { entries, restore, remove } = useAnalysisHistory();
  const toast = useToast();
  const navigate = useNavigate();

  /** Destaque do snapshot mais recente (primeiro da lista). */
  const newestId = entries[0]?.id ?? null;

  function confirmRestore(id: string) {
    if (
      !window.confirm(
        "Restaurar este snapshot substitui o modelo e a análise atuais na sessão. Continuar?",
      )
    ) {
      return;
    }
    restore(id);
    toast.success("Snapshot restaurado.");
    navigate("/analysis");
  }

  function handleExport(id: string) {
    if (
      !window.confirm("Restaurar e abrir a página de exportação com este snapshot?")
    ) {
      return;
    }
    restore(id);
    toast.info("Sessão atualizada. Escolha os formatos em Exportar.");
    navigate("/export");
  }

  async function handlePdf(id: string) {
    const e = entries.find((x) => x.id === id);
    if (!e) return;
    try {
      const blob = await generateReportPdfBlob(e.document, e.analysis);
      const safe = e.title.replace(/[^\w\-]+/g, "_").slice(0, 40);
      downloadPdfBlob(blob, `otm-report-${safe}-${e.createdAt}.pdf`);
      toast.success("PDF gerado a partir do snapshot.");
    } catch {
      toast.error("Falha ao gerar PDF.");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Sessão local"
        title="Histórico"
        description="Snapshots das últimas análises e exportações (localStorage, máx. 20). Cada entrada mostra métricas e um resumo JSON legível. Restaurar substitui o modelo e a análise em sessão."
      />

      {entries.length === 0 ? (
        <EmptyState
          title="Sem histórico ainda"
          description={
            <>
              Corra uma <strong className="text-otm-text">análise</strong> ou gere{" "}
              <strong className="text-otm-text">exportação / PDF</strong> para criar entradas aqui.
            </>
          }
        />
      ) : (
        <ul className="space-y-4" data-testid="history-list">
          {entries.map((e) => (
            <li key={e.id}>
              <HistoryCard
                entry={e}
                activeId={newestId}
                onRestore={confirmRestore}
                onExport={handleExport}
                onPdf={handlePdf}
                onRemove={(id) => {
                  remove(id);
                  toast.info("Entrada removida.");
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
