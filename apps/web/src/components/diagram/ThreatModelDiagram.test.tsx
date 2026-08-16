/**
 * `sanitizeDiagramLabel` é destrutivo por desenho, e é por isso que não pode tocar no documento.
 *
 * A sua própria docstring diz o que ele é: "Strips HTML and trims user-provided diagram labels …
 * The UI must never render raw HTML from these strings". É um filtro de **exibição**, e
 * `buildNodes`/`buildEdges` aplicam-no ao desenhar, que é o sítio certo.
 *
 * `updateSelectedLabel` aplicava-o também ao **gravar**, e por isso uma tecla no campo de nome do
 * inspector destruía o documento canónico:
 *
 *     antes:  "Customer DB <unencrypted, internet-facing>"
 *     digita: "!"
 *     depois: "Customer DB !"
 *
 * Sobrevivia ao reload, ia para o JSON exportado e para a lista de Componentes, sem undo. O campo
 * é controlado sobre o `name` cru, por isso o utilizador via a string inteira até ao instante em
 * que ela desaparecia. Alcançável sem devtools: `openapi_import.py:203` copia o `info.title` de um
 * spec de terceiros para `components[].name` tal e qual.
 *
 * **A interação vive no E2E, não aqui.** O React Flow arrasta com `d3-drag`, que precisa de um
 * `document` real; clicar num nó dentro do jsdom estoura em `nodrag.js`. O teste que exerce o
 * campo de nome está em `e2e/diagram.spec.ts`. O que este ficheiro fixa é a **premissa** que torna
 * o defeito possível — se alguém suavizar o filtro em vez de tirar a chamada do caminho de
 * gravação, o teste do E2E passaria a verde pela razão errada, e este falha.
 */

import { describe, expect, it } from "vitest";

import { sanitizeDiagramLabel } from "../../utils/diagramSanitize";

const HOSTILE = "Customer DB <unencrypted, internet-facing>";

describe("the display filter is lossy, which is why storage must not use it", () => {
  it("deletes bracketed text outright", () => {
    expect(sanitizeDiagramLabel(HOSTILE)).toBe("Customer DB");
  });

  it("loses the qualifier that inverts the meaning of the name", () => {
    expect(sanitizeDiagramLabel(HOSTILE)).not.toContain("unencrypted");
  });

  it("truncates, so a long name cannot round-trip through it either", () => {
    const long = "a".repeat(200);

    expect(sanitizeDiagramLabel(long).length).toBeLessThan(long.length);
  });
});
