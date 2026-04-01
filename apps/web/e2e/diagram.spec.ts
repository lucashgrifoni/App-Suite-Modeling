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
