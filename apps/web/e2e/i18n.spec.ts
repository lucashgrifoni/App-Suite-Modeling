import { expect, test } from "@playwright/test";

const LOCALE_KEY = "otm.web.locale";

test.describe("i18n pt-BR / en", () => {
  /**
   * Não usar addInitScript para limpar locale: ele corre em *toda* navegação, inclusive reload(),
   * e apagaria a persistência que o teste precisa validar. Cada teste usa contexto isolado (storage vazio).
   */

  test("seletor visível e troca para EN com texto representativo", async ({ page }) => {
    await page.goto("/");
    const switcher = page.getByTestId("language-switcher");
    await expect(switcher).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: /passo a passo/i })).toBeVisible();
    await switcher.selectOption("en");
    await expect(page.getByRole("heading", { level: 1, name: /step by step/i })).toBeVisible();
  });

  test("persistência após reload quando EN está selecionado", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("language-switcher").selectOption("en");
    await expect(page.getByRole("heading", { level: 1, name: /step by step/i })).toBeVisible();
    await expect
      .poll(async () => page.evaluate((key) => window.localStorage.getItem(key), LOCALE_KEY))
      .toBe("en");
    await page.reload();
    await expect(page.getByTestId("language-switcher")).toHaveValue("en");
    await expect(page.getByRole("heading", { level: 1, name: /step by step/i })).toBeVisible();
  });

  test("retorno a PT-BR", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("language-switcher").selectOption("en");
    await page.getByTestId("language-switcher").selectOption("pt-BR");
    await expect(page.getByRole("heading", { level: 1, name: /passo a passo/i })).toBeVisible();
  });
});
