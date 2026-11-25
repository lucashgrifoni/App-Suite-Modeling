/**
 * Nenhum acesso a `localStorage`/`sessionStorage` pode correr fora de `try`/`catch`.
 *
 * Nao e uma regra de estilo. `localStorage.getItem` **lanca** quando o browser recusa
 * storage — Safari em navegacao privada, Chrome com cookies de terceiros bloqueados, modo
 * quiosque — e um `getItem` desprotegido em `localePolicy.ts` rebentava durante o arranque
 * do i18n, antes de qualquer fronteira de erro do React estar montada. O ecra ficava em
 * branco: nao uma funcionalidade degradada, a app inteira.
 *
 * Esse era o unico caso na altura, e os outros 23 acessos ja estavam protegidos. E
 * precisamente por isso que a regra precisa de guarda automatica: o vigesimo quinto acesso
 * sera escrito por alguem que olha para os outros vinte e quatro, ve `try`/`catch` em todos,
 * e nao tem como saber que a suite nao verifica nenhum deles.
 */
import { describe, expect, it } from "vitest";

const SOURCES = import.meta.glob("../**/*.{ts,tsx}", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

const STORAGE = /\b(?:local|session)Storage\s*\./;

/** Um `try` aberto e ainda nao fechado por `catch` nas linhas anteriores da mesma regiao. */
function insideTry(lines: string[], index: number): boolean {
  let open = false;
  for (let j = Math.max(0, index - 25); j < index; j += 1) {
    if (/\btry\s*\{/.test(lines[j])) open = true;
    if (/\}\s*catch/.test(lines[j])) open = false;
  }
  return open;
}

function isComment(line: string): boolean {
  const t = line.trim();
  return t.startsWith("//") || t.startsWith("*") || t.startsWith("/*");
}

describe("acesso a storage do browser", () => {
  it("nunca corre fora de try/catch em codigo de producao", () => {
    const offenders: string[] = [];
    let checked = 0;

    for (const [path, src] of Object.entries(SOURCES)) {
      // Os testes montam storage a vontade; a regra e sobre o que vai para o browser.
      if (/\.test\.tsx?$/.test(path) || path.includes("/test/")) continue;
      const lines = src.split("\n");
      lines.forEach((line, i) => {
        if (isComment(line) || !STORAGE.test(line)) return;
        checked += 1;
        if (!insideTry(lines, i)) offenders.push(`${path}:${i + 1} ${line.trim().slice(0, 80)}`);
      });
    }

    // Sem isto o teste passaria com o glob partido, sem olhar para ficheiro nenhum.
    expect(checked).toBeGreaterThan(20);
    expect(offenders).toEqual([]);
  });
});
