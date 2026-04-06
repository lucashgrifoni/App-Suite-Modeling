import { expect, test } from "@playwright/test";

/** Jornada D — import assistido com resposta enriquecida (mock). */
test("import OpenAPI: inferências e navegação para revisão", async ({ page }) => {
  await page.route("**/api/v1/imports/openapi", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document: {
          model: {
            schema_version: "1.0.0",
            system_type: "web_application",
            industry_sector: "generic",
            methodology: "stride",
          },
          metadata: { title: "Import E2E", summary: "Rascunho mock", tags: [] },
          components: [{ id: "api", name: "API", kind: "process" }],
          data_flows: [],
          trust_boundaries: [],
          assets: [],
          threats: [],
          mitigations: [],
          evidence_suggestions: [],
        },
        inferences: [
          {
            id: "inf_e2e",
            message: "Superfície REST inferida (E2E).",
            confidence: "medium",
            source: "openapi",
            related_component_ids: ["api"],
          },
        ],
        unknowns: [],
        assumptions: [],
        explanations: [],
      }),
    });
  });

  await page.goto("/import");
  const fileInput = page.locator("#file");
  await fileInput.setInputFiles({
    name: "spec.yaml",
    mimeType: "text/yaml",
    buffer: Buffer.from("openapi: 3.0.0\ninfo:\n  title: E2E\n  version: '1'\npaths: {}\n"),
  });
  await page.getByRole("button", { name: "Gerar rascunho" }).click();
  await expect(page.getByText("Superfície REST inferida (E2E).")).toBeVisible({ timeout: 15000 });
  await page.goto("/review");
  await expect(page).toHaveURL(/\/review/);
});
