import type { TFunction } from "i18next";
import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";
import { localeFromUiLanguage, type ExportArtifactLocale } from "../i18n/exportArtifactLocale";
import i18n from "../i18n/i18n";

/**
 * Achata espaço em branco e trunca. **Não** remove `<…>`.
 *
 * Isto passava por `sanitizeDiagramLabel`, um removedor de tags herdado do caminho do diagrama.
 * Numa etiqueta de diagrama isso é aceitável; sobre prosa inverte o sentido — "The channel is
 * <not> encrypted" imprimia "The channel is encrypted", no artefacto que alguém arquiva como
 * evidência.
 *
 * E não comprava segurança nenhuma: este ficheiro desenha **texto**, não HTML — é o que a
 * docstring de `generateReportPdfBlob` já dizia — e o jsPDF escapa `(`, `)` e `\` ao construir o
 * content stream. Verificado com um payload cru `… ) Tj /JavaScript (app.alert\(1\)) …`: a string
 * não escapou e não apareceu chave `/JavaScript` nenhuma.
 */
function safeText(s: string, max = 2000): string {
  const flattened = s.replaceAll(/[^\S\r\n]+/g, " ").trim();
  return flattened.length > max ? `${flattened.slice(0, max - 1)}…` : flattened;
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

  // Quebrado em linhas como todo o resto. Era desenhado com um `pdf.text` directo, sem
  // `splitTextToSize`, por isso um título longo saía cortado na margem — dois relatórios com
  // versões diferentes no título produziam cabeçalhos pixel-idênticos e nomes de ficheiro iguais.
  pdf.setFontSize(16);
  for (const line of pdf.splitTextToSize(safeText(doc.metadata.title, 200), maxW)) {
    ensureSpace(10);
    pdf.text(line, margin, y);
    y += 8;
  }
  y += 2;

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
