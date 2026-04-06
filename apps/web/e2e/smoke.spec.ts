import { expect, test } from "@playwright/test";

test("fluxo mínimo UI: home -> análise -> export", async ({ page }) => {
  await page.route("**/api/v1/models", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        document: {
          model: {
            schema_version: "1.0.0",
            system_type: "web_application",
            industry_sector: "generic",
            methodology: "stride",
          },
          metadata: { title: "E2E Smoke Model", summary: "RC2 smoke" },
          components: [
            { id: "user", name: "User", kind: "user" },
            { id: "api", name: "API", kind: "process" },
          ],
          data_flows: [{ id: "f1", from_component: "user", to_component: "api", name: "request" }],
          trust_boundaries: [],
          assets: [],
          threats: [],
          mitigations: [],
          evidence_suggestions: [],
        },
      }),
    });
  });

  await page.route("**/api/v1/models/analyze", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        engine_version: "e2e-smoke",
        methodology: "stride",
        methodology_recommendation_reason: null,
        methodology_insights: null,
        document_title: "E2E Smoke Model",
        structural_findings: [],
        trust_boundary_findings: [],
        heuristic_threats: [
          {
            id: "eng_api_tampering",
            title: "Tampering no componente API",
            description: "Risco de alteração indevida",
            stride: "tampering",
            target_component_id: "api",
            target_data_flow_id: null,
            risk: { likelihood: 3, impact: 4, score: 12 },
            skipped_as_duplicate: false,
            framework_refs: [],
          },
        ],
        summary: {
          structural_findings: 0,
          trust_boundary_findings: 0,
          heuristic_threats_generated: 1,
          heuristic_threats_skipped_duplicate: 0,
          pack_threats_generated: 0,
          pack_threats_skipped_duplicate: 0,
          max_risk_score: 12,
          framework_ref_counts_by_catalog: {},
        },
        industry_pack_id: null,
        pack_control_hints: [],
      }),
    });
  });

  await page.route("**/api/v1/exports", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        artifacts: {
          analysis_markdown: "## Análise automática (motor)\n\n- Smoke ok",
          document_markdown: "# E2E Smoke Model",
        },
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Threat modeling, passo a passo" })).toBeVisible();

  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  await expect(page).toHaveURL(/\/wizard/);

  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await expect(page.getByText("Heurísticas novas")).toBeVisible();
  await expect(
    page.getByTestId("cockpit-priorities").getByText("Tampering no componente API"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Exportar resultados" }).click();
  await expect(page).toHaveURL(/\/export/);
  await page.getByRole("button", { name: "Gerar ficheiros" }).click();
  await expect(page.getByRole("heading", { name: "Descarregar" })).toBeVisible();
});
