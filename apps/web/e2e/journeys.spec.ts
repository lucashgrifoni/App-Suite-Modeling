import { expect, test } from "@playwright/test";

/** Documento mínimo para sessão (baseline diff / export). */
const sessionDocument = {
  model: {
    schema_version: "1.0.0",
    system_type: "web_application",
    industry_sector: "generic",
    methodology: "stride",
  },
  metadata: { title: "Journey E2E", summary: "baseline", tags: [] },
  components: [
    { id: "user", name: "User", kind: "user" },
    { id: "api", name: "API", kind: "process" },
  ],
  data_flows: [{ id: "f1", from_component: "user", to_component: "api", name: "req" }],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
};

const emptySection = { added: [] as string[], removed: [] as string[], modified: [] as unknown[] };

test("jornada análise enriquecida: cockpit, notas, trace, anti-patterns, pré-check", async ({ page }) => {
  await page.route("**/api/v1/models/analyze", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        engine_version: "e2e-journey",
        methodology: "stride",
        methodology_recommendation_reason: null,
        document_title: "Journey E2E",
        structural_findings: [],
        trust_boundary_findings: [],
        heuristic_threats: [
          {
            id: "eng_t1",
            title: "Risco heurístico E2E",
            description: "d",
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
        methodology_insights: null,
        industry_pack_id: null,
        pack_control_hints: [],
        explanations: [],
        model_quality_precheck: {
          score_0_100: 70,
          band: "good",
          methodology_fit: "partial",
          recommendation_confidence: "medium",
          methodology_fit_matrix: { stride: "strong" },
          checks: [{ code: "gap1", passed: false, message: "Lacuna E2E de pré-check." }],
        },
        wizard_context_notes: ["Assistente: nota de jornada E2E."],
        wizard_signal_trace: [
          {
            source_tag: "wz:api_backend_rest:cluster",
            effect: "observation",
            weight: "low",
            impact_areas: ["audit_only"],
            mechanism: "auxiliary",
            explanation: "Traço sintético para E2E.",
          },
        ],
        anti_pattern_hits: [
          {
            id: "ap_e2e_journey",
            name: "Anti-padrão E2E",
            severity_hint: "low",
            message: "Hit sintético.",
            evidence: ["e2e"],
            expected_controls: [],
          },
        ],
      }),
    });
  });

  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(sessionDocument));

  await page.goto("/analysis");
  await page.selectOption("#methodology", "stride");
  await page.getByRole("button", { name: "Gerar análise" }).click();
  await expect(page.getByTestId("cockpit-executive-strip")).toBeVisible();
  await expect(page.getByTestId("decision-cockpit")).toBeVisible();
  await expect(page.getByText("Assistente: nota de jornada E2E.")).toBeVisible();
  await expect(page.getByTestId("cockpit-guided-trace")).toBeVisible();
  await expect(page.getByTestId("cockpit-gaps").getByText("Lacuna E2E de pré-check.")).toBeVisible();
});

test("jornada diff enriquecido: semantic panel + refs estruturais", async ({ page }) => {
  const revised = {
    ...sessionDocument,
    components: [
      ...sessionDocument.components,
      { id: "svc_x", name: "Serviço novo", kind: "process" },
    ],
  };

  await page.route("**/api/v1/models/compare", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary: {
          headline: "E2E compare",
          has_structural_changes: true,
          has_analysis_changes: true,
          methodology_in_model_changed: false,
        },
        aggregate: {
          components: { added: ["svc_x"], removed: [], changed: [] },
          assets: { added: [], removed: [], changed: [] },
          data_flows: { added: [], removed: [], changed: [] },
          trust_boundaries: { added: [], removed: [], changed: [] },
          threats: { added: [], removed: [], changed: [] },
          mitigations: { added: [], removed: [], changed: [] },
          evidence_suggestions: { added: [], removed: [], changed: [] },
        },
        structural: {
          baseline_title: "Journey E2E",
          revised_title: "Journey E2E",
          summary_line: "Diff sintético E2E",
          model_info: [],
          metadata: [],
          business_context: [],
          residual_risk_summary: [],
          assets: emptySection,
          components: { added: ["svc_x"], removed: [], modified: [] },
          data_flows: emptySection,
          trust_boundaries: emptySection,
          threats: emptySection,
          mitigations: emptySection,
          evidence_suggestions: emptySection,
        },
        structural_insights: [],
        analysis: {
          methodology_before: "stride",
          methodology_after: "stride",
          methodology_changed: false,
          max_risk_before: 10,
          max_risk_after: 12,
          max_risk_delta: 2,
          heuristic_threats: { added: [], removed: [], modified: [] },
          framework_ref_counts: [],
          pack_control_hints: { added: [], removed: [] },
          signature_remap_hints: [],
        },
        analysis_insights: ["Heurística estável entre versões (E2E)."],
        risk_delta: {
          analysis_max_score_baseline: 10,
          analysis_max_score_revised: 12,
          analysis_max_score_delta: 2,
          heuristic_increased_ids: [],
          heuristic_decreased_ids: [],
          document_residual_aggregate_changed: false,
        },
        threat_delta: {
          canonical: { added: [], removed: [], modified: [] },
          heuristic: { added: [], removed: [], modified: [] },
        },
        recommendation_delta: {
          pack_hints_added: [],
          pack_hints_removed: [],
          framework_catalog_deltas: [],
          methodology_insight_blocks_added: [],
          methodology_insight_blocks_removed: [],
        },
        key_insights: ["E2E: componente novo no perímetro."],
        meta: {
          comparison_contract_version: "1.5",
          semantic_insights: ["Novo componente no grafo — rever superfície."],
          semantic_insights_version: "1.5",
          extensions: {},
          semantic_diff_sections: {
            structural_change_summary: ["Componentes: +1 / −0 / ~0"],
            improved: [],
            worsened: [],
            risk_impact: ["Superfície de gateway alterada no diff E2E."],
          },
          semantic_structural_refs: [
            {
              ref: "struct:component_added:svc_x",
              entity_kind: "component",
              entity_id: "svc_x",
              note: "Novo gateway no perímetro (E2E).",
              change_category: "component_added",
            },
          ],
          semantic_interpretation_links: [
            {
              structural_ref: "struct:component_added:svc_x",
              related_section: "risk_impact",
              summary: "Superfície de gateway alterada no diff E2E.",
              link_kind: "lexical_token_overlap",
              inference_strength: "medium",
              anchoring_rationale:
                "Vários tokens em comum entre a nota da ref estrutural e o bullet (gateway, perímetro).",
              shared_tokens: ["gateway", "perímetro"],
              entity_kind: "component",
            },
          ],
          interpretation_disclaimer: "Inferência correlacional — não causalidade provada (E2E).",
        },
        explanations: [],
      }),
    });
  });

  await page.addInitScript((docJson: string) => {
    sessionStorage.setItem("otm.web.document", docJson);
  }, JSON.stringify(sessionDocument));

  await page.goto("/diff");
  await page.locator("#revised-json").fill(JSON.stringify(revised));
  await page.getByRole("checkbox", { name: /Incluir análise/i }).check();
  await page.getByRole("button", { name: "Comparar" }).click();
  await expect(page.getByTestId("diff-semantic-panel")).toBeVisible();
  await expect(page.getByTestId("diff-structural-refs")).toBeVisible();
  await expect(
    page.getByTestId("diff-structural-refs").getByText("struct:component_added:svc_x"),
  ).toBeVisible();
  await expect(page.getByTestId("diff-interpretation-links")).toBeVisible();
  await expect(page.getByTestId("diff-interpretation-links")).toContainText("lexical_token_overlap");
});

test("jornada export com análise enriquecida: markdown contém secções guiadas", async ({ page }) => {
  const analysis = {
    engine_version: "e2e-export",
    methodology: "stride",
    document_title: "Journey E2E",
    structural_findings: [],
    trust_boundary_findings: [],
    heuristic_threats: [],
    summary: {
      structural_findings: 0,
      trust_boundary_findings: 0,
      heuristic_threats_generated: 0,
      heuristic_threats_skipped_duplicate: 0,
      pack_threats_generated: 0,
      pack_threats_skipped_duplicate: 0,
      max_risk_score: null,
      framework_ref_counts_by_catalog: {},
    },
    industry_pack_id: null,
    pack_control_hints: [],
    wizard_context_notes: ["Nota assistente export E2E."],
    wizard_signal_trace: [
      {
        source_tag: "wz:test=yes",
        effect: "observation",
        weight: "low",
        impact_areas: [],
        mechanism: "auxiliary",
        explanation: "Audit E2E export.",
      },
    ],
    anti_pattern_hits: [],
    model_quality_precheck: {
      score_0_100: 65,
      band: "good",
      methodology_fit: "partial",
      recommendation_confidence: "medium",
      methodology_fit_matrix: { stride: "partial" },
      checks: [],
    },
  };

  await page.route("**/api/v1/exports", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        artifacts: {
          analysis_markdown:
            "## Análise\n\n### Contexto do assistente (modelação guiada)\n\n- Nota assistente export E2E.\n\n### Rastreabilidade do assistente (audit trail)\n\n",
          document_markdown: "# Journey E2E",
        },
      }),
    });
  });

  await page.addInitScript(
    ({ docJson, anJson }: { docJson: string; anJson: string }) => {
      sessionStorage.setItem("otm.web.document", docJson);
      sessionStorage.setItem("otm.web.analysis", anJson);
    },
    { docJson: JSON.stringify(sessionDocument), anJson: JSON.stringify(analysis) },
  );

  await page.goto("/export");
  await page.getByRole("button", { name: "Gerar ficheiros" }).click();
  await expect(page.getByTestId("export-download-section")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Descarregar" })).toBeVisible();
});
