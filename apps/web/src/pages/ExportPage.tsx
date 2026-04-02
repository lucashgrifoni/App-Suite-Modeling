import { useState } from "react";
import { Navigate } from "react-router-dom";
import { exportArtifacts, fetchPremiumReport, type PremiumReportLevel } from "../api/otmApi";
import { ApiError } from "../api/client";
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
import type { ExportFormat } from "../types/api";

const FORMATS: { id: ExportFormat; label: string; hint: string }[] = [
  { id: "document_json", label: "Documento (JSON)", hint: "Modelo canónico" },
  { id: "document_markdown", label: "Documento (Markdown)", hint: "Relatório legível" },
  { id: "flowchart_mermaid", label: "Diagrama Mermaid", hint: "Flowchart LR" },
  { id: "analysis_json", label: "Análise (JSON)", hint: "Resultado completo do motor" },
  { id: "analysis_markdown", label: "Análise (Markdown)", hint: "Secção de relatório" },
  { id: "bundle_json", label: "Bundle (JSON)", hint: "Documento + análise num ficheiro" },
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

export function ExportPage() {
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
      const msg = "Escolha pelo menos um formato.";
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
      });
      setResult(artifacts);
      appendSnapshot("export");
      toast.success("Artefactos prontos para descarga.");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Exportação falhou.";
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
      const blob = await generateReportPdfBlob(model, analysis);
      const safe = model.metadata.title.replace(/[^\w\-]+/g, "_").slice(0, 40);
      downloadPdfBlob(blob, `otm-report-${safe}.pdf`);
      appendSnapshot("export");
      toast.success("PDF gerado.");
    } catch {
      const msg = "Falha ao gerar PDF.";
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
      });
      downloadPdfBlob(blob, filename);
      appendSnapshot("export");
      toast.success(kind === "pdf" ? "PDF premium gerado." : "Markdown premium descarregado.");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Falha no report premium.";
      setError(msg);
      toast.error(msg);
    } finally {
      setPremiumLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Entrega e evidências"
        title="Exportar"
        description={
          <>
            Gera ficheiros no browser. Formatos que incluem análise usam o último resultado em sessão;
            se faltar, o servidor corre o motor automaticamente.
          </>
        }
      />

      <div className="space-y-2 rounded-otm-lg border border-otm-border/80 bg-otm-surface-1/50 px-4 py-3">
        <WorkflowGuide variant="compact" />
        <ContextHint>
          Formatos com análise usam o último resultado em sessão; o <strong>diff</strong> compara JSON exportado com
          outra revisão.
        </ContextHint>
      </div>

      <Card title="Formatos" subtitle="Selecione o que precisa para relatório ou integração." variant="glass">
        <ul className="space-y-3">
          {FORMATS.map((f) => (
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
        <Button className="mt-4" onClick={() => void runExport()} disabled={loading || pdfLoading || premiumLoading}>
          {loading ? "A gerar…" : "Gerar ficheiros"}
        </Button>
      </Card>

      <Card
        title="Report premium (API)"
        subtitle="Executive / Standard / Deep — Markdown ou PDF alinhados ao motor e backlog (requer API em execução)."
        variant="elevated"
      >
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="premium-level" className="text-xs text-otm-text-muted">
              Nível
            </Label>
            <select
              id="premium-level"
              className="mt-1 block rounded-otm-md border border-otm-border bg-otm-surface-1 px-3 py-2 text-sm text-otm-text"
              value={premiumLevel}
              onChange={(e) => setPremiumLevel(e.target.value as PremiumReportLevel)}
            >
              <option value="executive">Executive</option>
              <option value="standard">Standard</option>
              <option value="deep">Deep technical</option>
            </select>
          </div>
          <Button
            variant="secondary"
            data-testid="export-premium-md"
            onClick={() => void runPremium("markdown")}
            disabled={premiumLoading || loading || pdfLoading}
          >
            {premiumLoading ? "A gerar…" : "Markdown premium"}
          </Button>
          <Button
            data-testid="export-premium-pdf"
            onClick={() => void runPremium("pdf")}
            disabled={premiumLoading || loading || pdfLoading}
          >
            {premiumLoading ? "A gerar…" : "PDF premium"}
          </Button>
        </div>
        <p className="mt-3 text-xs text-otm-text-muted">
          Se não houver análise em sessão, a API executa o motor automaticamente. O PDF usa o mesmo pipeline que a CLI.
        </p>
      </Card>

      <Card
        title="Relatório (PDF)"
        subtitle="Gerado no browser (jsPDF) — modelo e análise em sessão, sem chamada extra de API."
        variant="elevated"
      >
        <p className="text-sm text-otm-text-muted">
          Inclui título, resumo, métricas e ameaças (amostra). Conteúdo em texto plano para leitura segura.
        </p>
        <Button
          className="mt-4"
          data-testid="export-pdf"
          onClick={() => void runPdf()}
          disabled={pdfLoading || loading || premiumLoading}
        >
          {pdfLoading ? "A gerar PDF…" : "Gerar PDF"}
        </Button>
      </Card>

      {error && <Alert>{error}</Alert>}

      {result && (
        <Card title="Descarregar" subtitle="Ficheiros prontos para arquivo ou revisão." variant="elevated">
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
                  Descarregar
                </Button>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-otm-text-muted">
            Também pode copiar do preview técnico abaixo.
          </p>
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
      )}
    </div>
  );
}

function extFor(key: string): string {
  if (key.includes("mermaid")) return "mmd";
  if (key.includes("markdown")) return "md";
  return "json";
}

function mimeFor(key: string): string {
  if (key.includes("markdown")) return "text/markdown;charset=utf-8";
  if (key.includes("mermaid")) return "text/plain;charset=utf-8";
  return "application/json;charset=utf-8";
}
