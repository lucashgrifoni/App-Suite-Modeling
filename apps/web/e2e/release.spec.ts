import { expect, test, type Route } from "@playwright/test";

/** Mesmo contrato do smoke — mantém sessão consistente com a API mockada. */
function mockCreateModel(route: Route) {
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
        metadata: { title: "E2E Release Model", summary: "Release complementar" },
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
}

const REVISED_DOC = {
  model: {
    schema_version: "1.0.0",
    system_type: "web_application",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "E2E Revised", summary: null },
  components: [
    { id: "user", name: "User", kind: "user" },
    { id: "api", name: "API", kind: "process" },
    { id: "svc", name: "Service", kind: "process" },
  ],
  data_flows: [{ id: "f1", from_component: "user", to_component: "api", name: "request" }],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
};

function mockCompareResponse() {
  return {
    summary: {
      headline: "Diff E2E: alterações estruturais",
      has_structural_changes: true,
      has_analysis_changes: false,
      methodology_in_model_changed: false,
    },
    aggregate: {
      components: { added: ["svc"], removed: [], changed: [] },
      assets: { added: [], removed: [], changed: [] },
      data_flows: { added: [], removed: [], changed: [] },
      trust_boundaries: { added: [], removed: [], changed: [] },
      threats: { added: [], removed: [], changed: [] },
      mitigations: { added: [], removed: [], changed: [] },
      evidence_suggestions: { added: [], removed: [], changed: [] },
    },
    structural: {
      baseline_title: "E2E Release Model",
      revised_title: "E2E Revised",
      summary_line: "Resumo estrutural sintético (E2E).",
      model_info: [],
      metadata: [],
      business_context: [],
      residual_risk_summary: [],
      assets: { added: [], removed: [], modified: [] },
      components: { added: [], removed: [], modified: [] },
      data_flows: { added: [], removed: [], modified: [] },
      trust_boundaries: { added: [], removed: [], modified: [] },
      threats: { added: [], removed: [], modified: [] },
      mitigations: { added: [], removed: [], modified: [] },
      evidence_suggestions: { added: [], removed: [], modified: [] },
    },
    structural_insights: [],
    analysis: null,
    analysis_insights: [],
    risk_delta: {},
    threat_delta: {},
    recommendation_delta: {},
    key_insights: ["Componente svc adicionado (E2E)."],
    meta: {},
  };
}

test.describe("QA complementar (release)", () => {
  test("tema: Escuro e Claro aplicam data-theme no documento", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Tema da interface").selectOption("light");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page.getByLabel("Tema da interface").selectOption("dark");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("export: com sessão, cabeçalho e ação principal visíveis", async ({ page }) => {
    await page.route("**/api/v1/models", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      return mockCreateModel(route);
    });

    await page.goto("/");
    await page.getByRole("button", { name: "Criar novo modelo" }).click();
    await expect(page).toHaveURL(/\/wizard/);
    await page.goto("/export");
    await expect(page.getByRole("heading", { name: "Exportar" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Gerar ficheiros" })).toBeVisible();
  });

  test("diff: comparação com API mockada mostra resumo", async ({ page }) => {
    await page.route("**/api/v1/models", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      return mockCreateModel(route);
    });
    await page.route("**/api/v1/models/compare", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockCompareResponse()),
      });
    });

    await page.goto("/");
    await page.getByRole("button", { name: "Criar novo modelo" }).click();
    await page.goto("/diff");
    await page.locator("#revised-json").fill(JSON.stringify(REVISED_DOC));
    await page.getByRole("button", { name: "Comparar" }).click();
    await expect(page.getByRole("heading", { name: "Resumo" })).toBeVisible();
    await expect(page.getByText("Diff E2E: alterações estruturais").first()).toBeVisible();
    await expect(page.getByText("Componente svc adicionado (E2E).").first()).toBeVisible();
  });
});
