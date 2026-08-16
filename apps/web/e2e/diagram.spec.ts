import { expect, test } from "@playwright/test";
import { setupPhase4ApiMocks } from "./_phase4Mocks";

test("diagrama: modo editar por omissão e canvas visível", async ({ page }) => {
  await setupPhase4ApiMocks(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  await page.goto("/review");
  await expect(page.getByTestId("threat-model-flow")).toBeVisible();
  await expect(page.getByTestId("diagram-mode-toggle")).toHaveText("Visualizar");
  await expect(page.getByTestId("diagram-add-node")).toBeVisible();
  await page.getByTestId("diagram-mode-toggle").click();
  await expect(page.getByTestId("diagram-mode-toggle")).toHaveText("Editar");
  await expect(page.getByTestId("diagram-add-node")).not.toBeVisible();
});

test("diagrama: editar o nome não apaga o que está no modelo", async ({ page }) => {
  // `sanitizeDiagramLabel` é um filtro de exibição, e corria também na gravação: uma tecla no
  // campo de nome apagava `<…>` do documento canónico, sem undo, e a perda seguia para o JSON
  // exportado e para a lista de Componentes. O campo é controlado sobre o `name` cru, por isso o
  // utilizador via a string inteira até ao instante em que ela desaparecia.
  const HOSTILE = "Customer DB <unencrypted, internet-facing>";

  await setupPhase4ApiMocks(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();

  // Semeia um nome que o filtro de exibição mutila, através do estado que a app já usa.
  // A espera não é decorativa: sem ela o `evaluate` corre antes de a app ter escrito o documento
  // e o teste falha em "no document in session storage" — vermelho pela razão errada, que não
  // prova nada sobre o defeito.
  await page.waitForFunction(() => {
    const raw = sessionStorage.getItem("otm.web.document");
    return Boolean(raw && JSON.parse(raw).components?.length);
  });
  await page.evaluate((name) => {
    const raw = sessionStorage.getItem("otm.web.document");
    if (!raw) throw new Error("no document in session storage");
    const doc = JSON.parse(raw);
    doc.components[0].name = name;
    sessionStorage.setItem("otm.web.document", JSON.stringify(doc));
  }, HOSTILE);

  await page.goto("/review");
  await expect(page.getByTestId("threat-model-flow")).toBeVisible();
  await page.locator(".react-flow__node").first().click();

  const field = page.locator("#dm-label");
  await expect(field).toBeVisible();
  await expect(field).toHaveValue(HOSTILE);

  await field.press("End");
  await field.pressSequentially("!");

  // O que ficou GRAVADO, não o que está desenhado: o diagrama continua a sanitizar ao desenhar.
  const stored = await page.evaluate(() => {
    const raw = sessionStorage.getItem("otm.web.document");
    return raw ? JSON.parse(raw).components[0].name : null;
  });

  expect(stored).toContain("<unencrypted, internet-facing>");
});
