import { expect, test } from "@playwright/test";
import { setupPhase4ApiMocks } from "./_phase4Mocks";

test("export: gerar PDF inicia descarga", async ({ page }) => {
  await setupPhase4ApiMocks(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  await page.goto("/export");
  const dl = page.waitForEvent("download");
  await page.getByTestId("export-pdf").click();
  const download = await dl;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
});
