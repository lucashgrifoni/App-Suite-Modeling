/**
 * O PDF do cliente não pode reescrever o texto que imprime.
 *
 * Este ficheiro é o único renderizador do produto que **desenha texto**, e não HTML. A sua própria
 * docstring di-lo: "Texto apenas — evita XSS ao não embeddar HTML". Duas transformações herdadas de
 * caminhos HTML corriam sobre essa prosa e mudavam-lhe o sentido:
 *
 * **`safeText` passava tudo por `sanitizeDiagramLabel`**, um removedor de `<…>`. Numa etiqueta de
 * diagrama isso é aceitável; numa frase não:
 *
 *     "The channel is <not> encrypted"  ->  "The channel is  encrypted"
 *
 * O significado inverte-se, no artefacto que alguém arquiva como evidência. E não comprava nada:
 * o jsPDF escapa `(`, `)` e `\` ao construir o content stream — verificado na auditoria com um
 * payload cru `… ) Tj /JavaScript (app.alert\(1\)) …`, que não escapou da string nem produziu uma
 * chave `/JavaScript`. Não existe sink de HTML neste caminho.
 *
 * **`escapeValue: true` no i18next** escapava HTML para dentro do mesmo sink não-HTML: `CI/CD`
 * saía `CI&#x2F;CD` e `Bob's` saía `Bob&#39;s`. Em react-i18next o valor correto é `false`, e é o
 * que a documentação do i18next recomenda para React — o React escapa os seus text nodes de
 * qualquer forma. A premissa foi verificada: a app não tem um único `dangerouslySetInnerHTML` nem
 * `innerHTML`; a única ocorrência dessas palavras nos 133 ficheiros é um comentário a proibi-los.
 *
 * O título era ainda desenhado com `pdf.text` directo, sem `splitTextToSize`, por isso um título
 * longo saía cortado na margem — dois relatórios com versões diferentes no título produziam
 * cabeçalhos pixel-idênticos.
 */

import { describe, expect, it } from "vitest";

import type { OtmDocument } from "../types/document";
import { generateReportPdfBlob } from "./generateReportPdf";

/** `Blob.text()` não existe no polyfill do jsdom; latin1 é a codificação certa para o stream. */
async function blobText(blob: Blob): Promise<string> {
  if (typeof blob.arrayBuffer === "function") {
    return new TextDecoder("latin1").decode(await blob.arrayBuffer());
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsBinaryString(blob);
  });
}

/** Os operandos de texto do content stream, que é onde o que o leitor vê realmente está. */
async function drawnText(blob: Blob): Promise<string> {
  const raw = await blobText(blob);
  return [...raw.matchAll(/\((?:\\.|[^\\)])*\)\s*Tj/g)]
    .map((m) => m[0].slice(1, -3).replaceAll(/\\([()\\])/g, "$1"))
    .join("\n");
}

function documentWith(fields: Partial<Record<"title" | "summary", string>>): OtmDocument {
  return {
    model: { schema_version: "1.1.0", system_type: "web_application", industry_sector: "saas" },
    metadata: { title: fields.title ?? "Report", summary: fields.summary },
    components: [],
    trust_boundaries: [],
    data_flows: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  } as unknown as OtmDocument;
}

/** Análise mínima cujo `engine_version` chega ao PDF por interpolação do i18next. */
function analysisWith(engineVersion: string) {
  return {
    engine_version: engineVersion,
    heuristic_threats: [],
    summary: { heuristic_threats_generated: 0, max_risk_score: null },
  } as unknown as Parameters<typeof generateReportPdfBlob>[1];
}

describe("the PDF prints the words the author wrote", () => {
  it("keeps a qualifier written in angle brackets", async () => {
    const blob = await generateReportPdfBlob(
      documentWith({ summary: "The channel is <not> encrypted" }),
      null,
    );

    expect(await drawnText(blob)).toContain("<not>");
  });

  it("does not invert the meaning of the sentence", async () => {
    const blob = await generateReportPdfBlob(
      documentWith({ summary: "The channel is <not> encrypted" }),
      null,
    );

    expect(await drawnText(blob)).not.toMatch(/channel is\s+encrypted/);
  });

  // O escaping do i18next só atinge valores **interpolados** numa string de tradução, não texto
  // que o renderizador desenha directamente. `metadata.title` vai directo para `pdf.text`, por
  // isso um teste sobre o título passaria mesmo com `escapeValue: true` — passou, na primeira
  // versão deste ficheiro. O sink real é `t("artifactPdf.analysisLine", { engine })`.
  it("prints a slash as a slash in an interpolated value", async () => {
    const blob = await generateReportPdfBlob(documentWith({}), analysisWith("CI/CD-1.2"));

    const text = await drawnText(blob);
    expect(text).toContain("CI/CD-1.2");
    expect(text).not.toContain("&#x2F;");
  });

  it("prints an apostrophe as an apostrophe in an interpolated value", async () => {
    const blob = await generateReportPdfBlob(documentWith({}), analysisWith("Bob's build"));

    const text = await drawnText(blob);
    expect(text).toContain("Bob's");
    expect(text).not.toContain("&#39;");
  });
});

describe("the title is laid out, not clipped", () => {
  it("wraps a long title onto more than one line", async () => {
    const long =
      "Payment platform threat model for the quarterly review board covering ingress egress and settlement";

    const blob = await generateReportPdfBlob(documentWith({ title: long }), null);

    const lines = (await drawnText(blob)).split("\n");
    // A propriedade, sem depender de como o `splitTextToSize` corta: a primeira e a última
    // palavra do título têm de sair em linhas desenhadas **diferentes**. Sem quebra, ou saem na
    // mesma linha, ou a última nem chega a ser desenhada.
    const first = lines.findIndex((l) => l.includes("Payment"));
    const last = lines.findIndex((l) => l.includes("settlement"));

    expect(first).toBeGreaterThanOrEqual(0);
    expect(last).toBeGreaterThan(first);
  });

  it("keeps every word of the title", async () => {
    const long =
      "Payment platform threat model for the quarterly review board covering ingress egress and settlement";

    const blob = await generateReportPdfBlob(documentWith({ title: long }), null);

    const text = await drawnText(blob).then((t) => t.replaceAll("\n", " "));
    for (const word of ["Payment", "quarterly", "settlement"]) {
      expect(text).toContain(word);
    }
  });
});

describe("what the sanitiser removal must not break", () => {
  it("still collapses whitespace runs so layout stays predictable", async () => {
    const blob = await generateReportPdfBlob(
      documentWith({ summary: "spaced      out\ttext" }),
      null,
    );

    expect(await drawnText(blob)).not.toMatch(/ {3}/);
  });

  it("still produces a valid PDF", async () => {
    const blob = await generateReportPdfBlob(documentWith({ title: "Ordinary" }), null);

    expect((await blobText(blob)).startsWith("%PDF-")).toBe(true);
  });
});
