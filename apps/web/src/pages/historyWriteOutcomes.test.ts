/**
 * `appendSnapshot` devolve três resultados — `"ok"`, `"failed"` e `"evicted"` — e os dois
 * últimos só significam alguma coisa se quem chama disser ao utilizador o que aconteceu.
 * São quatro chamadores: um na Análise, três na Exportação.
 *
 * Os testes de comportamento em `AnalysisPage.test.tsx` cobrem o chamador da Análise a
 * sério, do armazenamento até ao toast. Os três da Exportação exigiriam harness próprio
 * cada um (PDF, premium), e o que se quer garantir deles é mais simples: que ninguém
 * acrescenta um chamador novo, ou apaga um ramo existente, sem que nada repare — foi assim
 * que `"evicted"` já foi uma vez calculado e deitado fora, com snapshots antigos a
 * desaparecer debaixo de um toast de sucesso sem ressalva.
 *
 * A contagem é o oráculo porque é falsificável nos dois sentidos: apagar um ramo põe o
 * teste vermelho, e acrescentar um chamador sem tratar os resultados também.
 */
import { describe, expect, it } from "vitest";

// `?raw` do Vite em vez de `node:fs`: este tsconfig nao carrega `@types/node`, e acrescenta-lo
// so por causa deste teste poria os globais de Node ao alcance do codigo da app, que e uma
// fronteira que vale mais do que a conveniencia.
const SOURCES = import.meta.glob("./{AnalysisPage,ExportPage}.tsx", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

function occurrences(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

describe("cada chamador de appendSnapshot trata os dois resultados de falha", () => {
  it.each(Object.keys(SOURCES))("%s", (path) => {
    const src = SOURCES[path];
    const callers = occurrences(src, "appendSnapshot(");

    expect(callers).toBeGreaterThan(0);
    expect({
      callers,
      full: occurrences(src, "history.toastStorageFull"),
      evicted: occurrences(src, "history.toastStorageEvicted"),
    }).toEqual({ callers, full: callers, evicted: callers });
  });
});
