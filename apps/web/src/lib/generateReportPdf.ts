import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";
import { sanitizeDiagramLabel } from "../utils/diagramSanitize";

function safeText(s: string, max = 2000): string {
  return sanitizeDiagramLabel(s, max).replace(/[^\S\r\n]+/g, " ");
}

/**
 * Gera PDF A4 no cliente (sem backend). Texto apenas — evita XSS ao não embeddar HTML.
 * Import dinâmico de `jspdf` para não inflar o chunk inicial.
 */
export async function generateReportPdfBlob(
  doc: OtmDocument,
  analysis: AnalysisResult | null,
): Promise<Blob> {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ unit: "mm", format: "a4" });
  const margin = 16;
  const pageW = pdf.internal.pageSize.getWidth();
  const maxW = pageW - 2 * margin;
  let y = 18;
  const lineH = 5.5;

  const ensureSpace = (needed: number) => {
    if (y + needed > 285) {
      pdf.addPage();
      y = margin;
    }
  };

  const addLines = (text: string, fontSize = 10) => {
    pdf.setFontSize(fontSize);
    const lines = pdf.splitTextToSize(text, maxW);
    for (const line of lines) {
      ensureSpace(lineH);
      pdf.text(line, margin, y);
      y += lineH;
    }
  };

  pdf.setFontSize(16);
  ensureSpace(10);
  pdf.text(safeText(doc.metadata.title, 200), margin, y);
  y += 10;

  if (doc.metadata.summary) {
    addLines(`Resumo: ${safeText(doc.metadata.summary ?? "", 500)}`, 10);
  }

  addLines(
    `Sistema: ${safeText(doc.model.system_type)} · Metodologia: ${safeText(String(doc.model.methodology ?? "stride"))}`,
    9,
  );
  addLines(`Componentes: ${doc.components.length} · Fluxos: ${doc.data_flows.length}`, 10);

  if (analysis) {
    y += 4;
    ensureSpace(8);
    pdf.setFontSize(12);
    pdf.text("Análise (motor)", margin, y);
    y += 8;
    addLines(
      `Motor: ${safeText(analysis.engine_version)} · Heurísticas novas: ${analysis.summary.heuristic_threats_generated} · Maior L×I: ${analysis.summary.max_risk_score ?? "—"}`,
    );
    const threats = analysis.heuristic_threats.filter((t) => !t.skipped_as_duplicate).slice(0, 30);
    if (threats.length) {
      addLines("Ameaças (amostra):", 11);
      for (const t of threats) {
        addLines(`• ${safeText(t.title, 200)} — STRIDE ${t.stride} — L×I ${t.risk.score ?? "—"}`, 9);
      }
    }
  } else {
    y += 4;
    addLines("Análise ainda não disponível neste relatório.", 10);
  }

  return pdf.output("blob");
}

export function downloadPdfBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = globalThis.document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
