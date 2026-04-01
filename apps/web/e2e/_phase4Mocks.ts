import type { Page } from "@playwright/test";

/** Mocks mínimos para fluxos com modelo + análise + export (E2E fase 4). */
export async function setupPhase4ApiMocks(page: Page) {
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
          metadata: { title: "Phase4 E2E Model", summary: "diagram + pdf + history" },
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
        engine_version: "e2e-phase4",
        methodology: "stride",
        methodology_recommendation_reason: null,
        methodology_insights: null,
        document_title: "Phase4 E2E Model",
        structural_findings: [],
        trust_boundary_findings: [],
        heuristic_threats: [
          {
            id: "t1",
            title: "Test threat",
            description: "x",
            stride: "spoofing",
            target_component_id: "api",
            target_data_flow_id: null,
            risk: { likelihood: 2, impact: 3, score: 6 },
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
          max_risk_score: 6,
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
          document_markdown: "# Phase4",
          analysis_markdown: "## A",
        },
      }),
    });
  });
}
