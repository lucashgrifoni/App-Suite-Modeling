/**
 * Fluxos críticos com API FastAPI real (sem mocks de fetch).
 * Executar: npm run e2e:hybrid (requer Python + otm_api instalado).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const minimalDoc = JSON.parse(
  readFileSync(path.join(__dirname, "fixtures", "minimal-document.json"), "utf-8"),
) as Record<string, unknown>;

test("híbrido: análise real — cockpit e pré-check a partir do motor", async ({ page }) => {
  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(minimalDoc));

  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();

  await expect(page.getByTestId("cockpit-executive-strip")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("decision-cockpit")).toBeVisible();
  await expect(page.getByText(/pré-check/i).first()).toBeVisible();
  await expect(page.getByTestId("cockpit-priorities")).toBeVisible();
});

test("híbrido: compare real — diff semântico e meta v1.4", async ({ page }) => {
  const revised = {
    ...minimalDoc,
    components: [
      ...(minimalDoc.components as object[]),
      { id: "hybrid_svc", name: "Serviço híbrido", kind: "process" },
    ],
  };

  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(minimalDoc));

  await page.goto("/diff");
  await page.locator("#revised-json").fill(JSON.stringify(revised));
  await page.getByRole("checkbox", { name: /Incluir análise/i }).check();
  await page.getByRole("button", { name: "Comparar" }).click();

  await expect(page.getByTestId("diff-semantic-panel")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("diff-structural-refs")).toBeVisible();
  // `semantic_interpretation_links` pode estar vazio (v1.4) — validar mudança estrutural na UI.
  await expect(page.getByText("Estrutura", { exact: true })).toBeVisible();
});

test("híbrido: export real — artefactos com análise do motor", async ({ page }) => {
  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(minimalDoc));

  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await expect(page.getByTestId("cockpit-priorities")).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Exportar resultados" }).click();
  await expect(page).toHaveURL(/\/export/);
  await page.getByRole("button", { name: "Gerar ficheiros" }).click();
  await expect(page.getByRole("heading", { name: "Descarregar" })).toBeVisible({ timeout: 60_000 });
});
