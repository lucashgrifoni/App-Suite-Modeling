import type { TFunction } from "i18next";
import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";
import { localeFromUiLanguage, type ExportArtifactLocale } from "../i18n/exportArtifactLocale";
import i18n from "../i18n/i18n";
import { sanitizeDiagramLabel } from "../utils/diagramSanitize";

function safeText(s: string, max = 2000): string {
  return sanitizeDiagramLabel(s, max).replaceAll(/[^\S\r\n]+/g, " ");
}

function pdfT(lng: ExportArtifactLocale): TFunction {
  return i18n.getFixedT(lng);
}

/**
 * Gera PDF A4 no cliente (sem backend). Texto apenas — evita XSS ao não embeddar HTML.
 * Import dinâmico de `jspdf` para não inflar o chunk inicial.
 *
 * @param options.locale - Idioma dos rótulos do PDF; quando omitido, usa o idioma atual do i18n.
 */
export async function generateReportPdfBlob(
  doc: OtmDocument,
  analysis: AnalysisResult | null,
  options?: { locale?: ExportArtifactLocale },
): Promise<Blob> {
  const lng: ExportArtifactLocale = options?.locale ?? localeFromUiLanguage(i18n.language);
  const t = pdfT(lng);
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
    addLines(`${t("artifactPdf.summary")} ${safeText(doc.metadata.summary ?? "", 500)}`, 10);
  }

  addLines(
    t("artifactPdf.systemMethodology", {
      system: safeText(doc.model.system_type),
      methodology: safeText(String(doc.model.methodology ?? "stride")),
    }),
    9,
  );
  addLines(
    t("artifactPdf.counts", {
      components: doc.components.length,
      flows: doc.data_flows.length,
    }),
    10,
  );

  if (analysis) {
    y += 4;
    ensureSpace(8);
    pdf.setFontSize(12);
    pdf.text(t("artifactPdf.analysisHeading"), margin, y);
    y += 8;
    addLines(
      t("artifactPdf.analysisLine", {
        engine: safeText(analysis.engine_version),
        new: analysis.summary.heuristic_threats_generated,
        max: analysis.summary.max_risk_score ?? "—",
      }),
    );
    const threats = analysis.heuristic_threats.filter((th) => !th.skipped_as_duplicate).slice(0, 30);
    if (threats.length) {
      addLines(t("artifactPdf.threatsSample"), 11);
      for (const th of threats) {
        addLines(
          t("artifactPdf.threatBullet", {
            title: safeText(th.title, 200),
            stride: th.stride,
            score: th.risk.score ?? "—",
          }),
          9,
        );
      }
    }
  } else {
    y += 4;
    addLines(t("artifactPdf.noAnalysis"), 10);
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
