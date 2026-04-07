import { describe, expect, it } from "vitest";
import type { OtmDocument } from "../types/document";
import {
  applyDataFlowIdRename,
  applyKnownComponentIdTypoFixes,
} from "./documentNormalize";

function minimalDoc(overrides: Partial<OtmDocument> = {}): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title: "T", tags: [] },
    components: [],
    data_flows: [],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
    ...overrides,
  };
}

describe("applyKnownComponentIdTypoFixes", () => {
  it("renames worke to worker and updates flows and trust boundary refs", () => {
    const doc = minimalDoc({
      components: [
        { id: "api", name: "API", kind: "process" },
        { id: "worke", name: "Worker", kind: "process" },
      ],
      data_flows: [
        { id: "f1", from_component: "api", to_component: "worke" },
        { id: "f2", from_component: "worke", to_component: "api" },
      ],
      assets: [
        {
          id: "a1",
          name: "A",
          related_component_ids: ["worke"],
        },
      ],
      trust_boundaries: [
        {
          id: "tb1",
          name: "Zona",
          member_component_ids: ["worke"],
          outside_component_ids: [],
        },
      ],
    });
    const fixed = applyKnownComponentIdTypoFixes(doc);
    expect(fixed.components.map((c) => c.id)).toEqual(["api", "worker"]);
    expect(fixed.data_flows[0].to_component).toBe("worker");
    expect(fixed.data_flows[1].from_component).toBe("worker");
    expect(fixed.assets[0].related_component_ids).toEqual(["worker"]);
    expect(fixed.trust_boundaries[0].member_component_ids).toEqual(["worker"]);
  });

  it("does not rename when worker already exists", () => {
    const doc = minimalDoc({
      components: [
        { id: "worker", name: "W1", kind: "process" },
        { id: "worke", name: "W2", kind: "process" },
      ],
    });
    const fixed = applyKnownComponentIdTypoFixes(doc);
    expect(fixed.components.map((c) => c.id).sort()).toEqual(["worke", "worker"]);
  });

  it("leaves document unchanged when worke is absent", () => {
    const doc = minimalDoc({
      components: [{ id: "worker", name: "W", kind: "process" }],
    });
    const fixed = applyKnownComponentIdTypoFixes(doc);
    expect(fixed).toEqual(doc);
  });
});

describe("applyDataFlowIdRename", () => {
  it("updates assets, trust boundaries, and threat target_data_flow_id", () => {
    const doc = minimalDoc({
      components: [
        { id: "user", name: "U", kind: "user" },
        { id: "api", name: "API", kind: "process" },
      ],
      data_flows: [
        { id: "f_new", from_component: "user", to_component: "api", name: "Ingress" },
      ],
      assets: [
        {
          id: "a1",
          name: "Credenciais",
          related_data_flow_ids: ["to_waf", "waf_api"],
        },
      ],
      trust_boundaries: [
        {
          id: "internet",
          name: "Internet",
          crossing_flow_ids: ["to_waf"],
        },
      ],
      threats: [
        {
          id: "t1",
          title: "Spoof",
          stride: "spoofing",
          target_data_flow_id: "to_waf",
        },
      ],
    });
    const out = applyDataFlowIdRename(doc, "to_waf", "f_new");
    expect(out.assets[0].related_data_flow_ids).toEqual(["f_new", "waf_api"]);
    expect(out.trust_boundaries[0].crossing_flow_ids).toEqual(["f_new"]);
    expect((out.threats[0] as { target_data_flow_id?: string }).target_data_flow_id).toBe(
      "f_new",
    );
  });

  it("does not rewrite when two flows share the target id", () => {
    const doc = minimalDoc({
      components: [{ id: "a", name: "A", kind: "process" }],
      data_flows: [
        { id: "x", from_component: "a", to_component: "a" },
        { id: "x", from_component: "a", to_component: "a" },
      ],
      assets: [{ id: "a1", name: "A", related_data_flow_ids: ["old"] }],
    });
    const out = applyDataFlowIdRename(doc, "old", "x");
    expect(out.assets[0].related_data_flow_ids).toEqual(["old"]);
  });
});
