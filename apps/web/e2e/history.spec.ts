import { expect, test } from "@playwright/test";
import { setupPhase4ApiMocks } from "./_phase4Mocks";

test("histórico: entrada após análise", async ({ page }) => {
  await setupPhase4ApiMocks(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await expect(page.getByText("Heurísticas novas")).toBeVisible();
  await page.goto("/history");
  await expect(page.getByTestId("history-list")).toBeVisible();
  await expect(page.getByText("Phase4 E2E Model").first()).toBeVisible();
});
