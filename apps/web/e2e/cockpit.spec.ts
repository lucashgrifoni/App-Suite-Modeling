import { expect, test } from "@playwright/test";

/** Análise enriquecida mockada — smoke do cockpit sem backend real. */
const enrichedAnalysisBody = {
  engine_version: "e2e-cockpit",
  methodology: "stride",
  methodology_recommendation_reason: null,
  methodology_insights: null,
  document_title: "Cockpit E2E",
  structural_findings: [],
  trust_boundary_findings: [],
  heuristic_threats: [
    {
      id: "eng_api_tampering",
      title: "Tampering API (prioridade)",
      description: "Teste",
      stride: "tampering",
      target_component_id: "api",
      target_data_flow_id: null,
      risk: { likelihood: 4, impact: 5, score: 20 },
      skipped_as_duplicate: false,
      framework_refs: [],
    },
    {
      id: "eng_api_spoofing",
      title: "Spoofing API",
      description: "Teste",
      stride: "spoofing",
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
    heuristic_threats_generated: 2,
    heuristic_threats_skipped_duplicate: 0,
    pack_threats_generated: 0,
    pack_threats_skipped_duplicate: 0,
    max_risk_score: 20,
    framework_ref_counts_by_catalog: {},
  },
  industry_pack_id: null,
  pack_control_hints: [],
  explanations: [],
  wizard_context_notes: ["Assistente: contexto de upload reforçado (E2E)."],
  wizard_signal_trace: [
    {
      source_tag: "wz:file_handling_application:cluster",
      effect: "ranking_impact",
      weight: "moderate",
      impact_areas: ["heuristic_ranking"],
      mechanism: "contextual",
      explanation: "Traço de auditoria sintético para E2E.",
    },
  ],
  model_quality_precheck: {
    score_0_100: 72,
    band: "good",
    methodology_fit: "partial",
    recommendation_confidence: "medium",
    methodology_fit_matrix: { stride: "strong" },
    checks: [
      { code: "c1", passed: true, message: "OK" },
      { code: "gap_x", passed: false, message: "Falta mapear fluxo sensível (E2E)." },
    ],
  },
  anti_pattern_hits: [
    {
      id: "ap_e2e",
      name: "Anti-padrão E2E",
      severity_hint: "medium",
      message: "Sinal de modelagem a rever.",
      evidence: ["e2e"],
      expected_controls: [],
    },
  ],
};

test("cockpit: blocos principais com análise enriquecida mockada", async ({ page }) => {
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
          metadata: { title: "Cockpit E2E", summary: "e2e" },
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
      body: JSON.stringify(enrichedAnalysisBody),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Criar novo modelo" }).click();
  await expect(page).toHaveURL(/\/wizard/);
  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();

  await expect(page.getByTestId("cockpit-executive-strip")).toBeVisible();
  await expect(page.getByTestId("decision-cockpit")).toBeVisible();
  await expect(page.getByTestId("cockpit-priorities")).toContainText("Tampering API");
  await expect(page.getByTestId("cockpit-gaps")).toContainText("Falta mapear fluxo sensível");
  await expect(page.getByTestId("cockpit-wizard-signals")).toContainText("Assistente:");
  await expect(page.getByTestId("model-quality-strip")).toBeVisible();
  await expect(page.getByTestId("model-quality-strip")).toContainText("Anti-padrões");
  await expect(page.getByTestId("cockpit-guided-trace")).toBeVisible();
});
