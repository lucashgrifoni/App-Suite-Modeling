import { expect, test } from "@playwright/test";
import { setupPhase4ApiMocks } from "./_phase4Mocks";

/**
 * O wizard é a maior página do produto (793 linhas) e a principal superfície de autoria — e a
 * auditoria de 2026-08-20 registou que **nenhuma lente a tinha aberto**. Os specs existentes
 * semeiam estado e dirigem análise e export; nenhum escrevia num campo do wizard.
 *
 * O invariante é o mesmo que um defeito confirmado no inspector do diagrama violava (`02834b2`):
 * o que o utilizador escreve é o que fica guardado. Lá, um filtro de exibição corria no caminho
 * de gravação e apagava `<…>` do documento canónico a cada tecla.
 *
 * Aqui, a inspeção mostra o wizard já correto — `value={c.name}` sobre o valor cru, `onChange`
 * grava verbatim, e os cinco `.trim()` estão todos em `onBlur`, com um comentário no código a
 * explicar porquê ("keeps the space the user just typed from vanishing mid-word"). Estes testes
 * existem para **fixar** isso, porque a superfície irmã já provou que a regra pode ser quebrada
 * sem ninguém reparar.
 */

const HOSTILE = "Customer DB <unencrypted, internet-facing>";

async function openWizardWithOneComponent(page: import("@playwright/test").Page) {
  await setupPhase4ApiMocks(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  await page.waitForFunction(() => {
    const raw = sessionStorage.getItem("otm.web.document");
    return Boolean(raw && JSON.parse(raw).components?.length);
  });
  await page.goto("/wizard");
  // O wizard é um stepper de quatro passos e abre no 0 (Contexto). Semear
  // `otm.web.wizard.step` não serve: todo o produtor de um documento novo chama
  // `clearWizardStep`, e essa limpeza corre depois de o documento aparecer na sessão — a chave
  // semeada desaparecia numas execuções e não noutras. Clicar no separador é determinístico,
  // porque `furthestStepForDocument` desbloqueia até ao passo 2 assim que há um componente.
  await page.getByRole("button", { name: /Componentes/ }).click();
  await page.waitForSelector("#comp-0-name");
}

async function storedNames(page: import("@playwright/test").Page): Promise<string[]> {
  return page.evaluate(() => {
    const raw = sessionStorage.getItem("otm.web.document");
    return raw ? JSON.parse(raw).components.map((c: { name: string }) => c.name) : [];
  });
}

test("wizard: o nome escrito é o nome guardado, incluindo `<…>`", async ({ page }) => {
  await openWizardWithOneComponent(page);
  const field = page.locator("#comp-0-name");
  await expect(field).toBeVisible();

  await field.fill(HOSTILE);
  await field.blur();

  expect((await storedNames(page))[0]).toBe(HOSTILE);
});

test("wizard: um espaço no meio da palavra não desaparece enquanto se escreve", async ({ page }) => {
  // Os cinco `.trim()` desta página estão em `onBlur` de propósito. Se algum migrar para
  // `onChange` num campo controlado sobre o valor guardado, o espaço é comido a cada tecla e o
  // utilizador não consegue escrever duas palavras. Este teste falha nesse dia.
  await openWizardWithOneComponent(page);
  const field = page.locator("#comp-0-name");

  await field.click();
  await field.press("ControlOrMeta+a");
  await field.pressSequentially("Edge gateway");

  await expect(field).toHaveValue("Edge gateway");
});

/**
 * Documento com um fluxo que depende do componente, para que remover o componente dispare o
 * aviso de cascata — o único sítio do wizard onde o nome escrito pelo utilizador vira conteúdo
 * renderizado em vez de `value` de um `<input>`.
 */
const DOC_WITH_HOSTILE_NAME = {
  model: {
    schema_version: "1.0.0",
    system_type: "web_application",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "Wizard E2E", summary: "cascade", tags: [] },
  components: [
    { id: "user", name: "</h2><h2>Aprovado</h2><table><tr><td>x", kind: "user" },
    { id: "api", name: "API", kind: "process" },
  ],
  data_flows: [{ id: "f1", from_component: "user", to_component: "api", name: "req" }],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
};

test("wizard: o aviso de cascata não deixa o nome do componente virar estrutura", async ({ page }) => {
  // A primeira versão deste teste escrevia a marcação no campo do nome e contava estrutura na
  // página. Não podia falhar: nesse passo o nome só existe como `value` de um `<input>`, e um
  // atributo de valor não introduz cabeçalhos nem tabelas — nenhuma mutação a punha vermelha.
  //
  // O nome só vira conteúdo renderizado num sítio: `t("wizard.removeCascadedToFlows", { name })`,
  // cujo texto o toast mostra. Esse sítio é sensível à decisão desta campanha de pôr
  // `escapeValue: false` no i18next, tomada porque a app não tem um único sink de HTML. Este
  // teste fixa essa premissa onde ela é efectivamente exercida.
  await setupPhase4ApiMocks(page);
  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(DOC_WITH_HOSTILE_NAME));
  await page.goto("/wizard");
  await page.getByRole("button", { name: /Componentes/ }).click();
  await page.waitForSelector("#comp-0-name");

  const count = async () => page.locator("h1, h2, h3, table").count();
  const before = await count();

  await page.getByRole("button", { name: /Remover/ }).first().click();
  const toast = page.getByText(/Aprovado/);
  await expect(toast).toBeVisible();

  expect(await count()).toBe(before);
});

test("wizard: um nome só com espaços cai para o id em vez de ficar em branco", async ({ page }) => {
  // Contrato declarado no próprio código: um nome vazio produziria um nó Mermaid vazio e
  // `- **   ** (id)` no Markdown, por isso o id fica no lugar.
  await openWizardWithOneComponent(page);
  const field = page.locator("#comp-0-name");

  await field.fill("     ");
  await field.blur();

  const [name] = await storedNames(page);
  expect(name.trim()).not.toBe("");
});
