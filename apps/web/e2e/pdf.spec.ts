import { expect, test } from "@playwright/test";
import { setupPhase4ApiMocks } from "./_phase4Mocks";

test("export: gerar PDF inicia descarga", async ({ page }) => {
  await setupPhase4ApiMocks(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  // createBlankModel is async; wizard navigation alone is not enough for a full page.load of /export
  // (ExportPage reads document from sessionStorage on mount).
  await expect(page).toHaveURL(/\/wizard/);
  await page.waitForFunction(
    () => {
      try {
        const raw = sessionStorage.getItem("otm.web.document");
        return Boolean(raw && raw.length > 20);
      } catch {
        return false;
      }
    },
    { timeout: 15_000 },
  );

  await page.goto("/export");
  await page.waitForLoadState("domcontentloaded");
  await expect(page).toHaveURL(/\/export/);

  const pdfBtn = page.getByTestId("export-pdf");
  await expect(pdfBtn).toBeVisible();
  await expect(pdfBtn).toBeEnabled();

  const [download] = await Promise.all([page.waitForEvent("download"), pdfBtn.click()]);
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
});
