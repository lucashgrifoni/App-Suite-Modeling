import { describe, expect, it } from "vitest";
import { removeComponents, removeDataFlows } from "./documentNormalize";
import { applyComponentIdRename, nextEntityId } from "./wizardEdits";
import type { OtmDocument } from "../types/document";

function doc(partial: Partial<OtmDocument> = {}): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title: "Fixture", tags: [] },
    components: [],
    data_flows: [],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
    ...partial,
  };
}

describe("nextEntityId", () => {
  it("starts at 1 on an empty grid", () => {
    expect(nextEntityId("comp_", [])).toBe("comp_1");
  });

  it("skips ids already in use", () => {
    expect(nextEntityId("comp_", ["comp_1", "comp_2"])).toBe("comp_3");
  });

  it("reuses a number freed by a removal instead of colliding with the survivor", () => {
    // The whole point: `comp_${components.length + 1}` returned "comp_2" here, which is
    // the id of the row that is still on screen.
    expect(nextEntityId("comp_", ["comp_2"])).toBe("comp_1");
  });

  it("ignores ids that do not follow the prefix_<n> shape", () => {
    expect(nextEntityId("comp_", ["gateway", "comp_x", "comp_"])).toBe("comp_1");
  });

  it("does not collide with a hand-typed id that happens to match the pattern", () => {
    expect(nextEntityId("flow_", ["flow_1", "flow_3"])).toBe("flow_2");
  });

  it("never repeats when called in sequence over its own output", () => {
    const taken: string[] = [];
    for (let i = 0; i < 50; i += 1) taken.push(nextEntityId("comp_", taken));
    expect(new Set(taken).size).toBe(50);
  });
});

describe("add / remove / add, the sequence that produced duplicate ids", () => {
  it("mints three distinct component ids across a removal", () => {
    // Exactly the reported repro: add, add, remove the first row, add.
    let d = doc();
    const add = () => {
      d = {
        ...d,
        components: [
          ...d.components,
          { id: nextEntityId("comp_", d.components.map((c) => c.id)), name: "New", kind: "process" },
        ],
      };
    };

    add();
    add();
    d = removeComponents(d, [d.components[0].id]);
    add();

    const ids = d.components.map((c) => c.id);
    expect(ids).toEqual(["comp_2", "comp_1"]);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("mints three distinct flow ids across a removal", () => {
    let d = doc({
      components: [
        { id: "a", name: "A", kind: "process" },
        { id: "b", name: "B", kind: "process" },
      ],
    });
    const add = () => {
      d = {
        ...d,
        data_flows: [
          ...d.data_flows,
          {
            id: nextEntityId("flow_", d.data_flows.map((f) => f.id)),
            from_component: "a",
            to_component: "b",
            name: null,
          },
        ],
      };
    };

    add();
    add();
    d = removeDataFlows(d, ["flow_1"]);
    add();

    const ids = d.data_flows.map((f) => f.id);
    expect(ids).toEqual(["flow_2", "flow_1"]);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("applyComponentIdRename", () => {
  const renamed = () =>
    doc({
      // The wizard's onChange has already written the new id into the row; the helper
      // only has to carry it into everything that pointed at the old one.
      components: [
        { id: "a2", name: "A", kind: "process" },
        { id: "b", name: "B", kind: "process" },
      ],
      data_flows: [
        { id: "f1", from_component: "a", to_component: "b", name: null },
        { id: "f2", from_component: "b", to_component: "a", name: null },
      ],
      assets: [{ id: "asset1", name: "Data", related_component_ids: ["a", "b"] }],
      trust_boundaries: [
        {
          id: "tb1",
          name: "Edge",
          member_component_ids: ["a"],
          outside_component_ids: ["b", "a"],
        },
      ],
      threats: [
        { id: "t1", title: "T", target_component_id: "a" },
        { id: "t2", title: "T2", target_component_id: "b" },
      ],
    });

  it("leaves no reference pointing at the old id", () => {
    const out = applyComponentIdRename(renamed(), "a", "a2");
    expect(JSON.stringify(out)).not.toContain('"a"');
  });

  it("rewrites data-flow endpoints", () => {
    const out = applyComponentIdRename(renamed(), "a", "a2");
    expect(out.data_flows[0].from_component).toBe("a2");
    expect(out.data_flows[1].to_component).toBe("a2");
  });

  it("rewrites asset and trust-boundary membership without touching other ids", () => {
    const out = applyComponentIdRename(renamed(), "a", "a2");
    expect(out.assets[0].related_component_ids).toEqual(["a2", "b"]);
    expect(out.trust_boundaries[0].member_component_ids).toEqual(["a2"]);
    expect(out.trust_boundaries[0].outside_component_ids).toEqual(["b", "a2"]);
  });

  it("rewrites threat targets, which the canonical schema also validates", () => {
    const out = applyComponentIdRename(renamed(), "a", "a2");
    expect((out.threats[0] as { target_component_id: string }).target_component_id).toBe("a2");
    expect((out.threats[1] as { target_component_id: string }).target_component_id).toBe("b");
  });

  it("does not materialise optional lists that were absent", () => {
    // Checked on the serialised document because that is what reaches sessionStorage and
    // the API. Like its siblings in documentNormalize the helper spreads `?.map(...)`, so
    // the key exists in memory holding `undefined`; JSON.stringify drops it. An empty array
    // would NOT be dropped, and would turn "no membership stated" into "membership: none".
    const before = doc({
      components: [{ id: "a2", name: "A", kind: "process" }],
      assets: [{ id: "asset1", name: "Data" }],
      trust_boundaries: [{ id: "tb1", name: "Edge" }],
    });
    const out = JSON.parse(JSON.stringify(applyComponentIdRename(before, "a", "a2")));
    expect("related_component_ids" in out.assets[0]).toBe(false);
    expect("member_component_ids" in out.trust_boundaries[0]).toBe(false);
  });

  it("does nothing when the ids are empty or unchanged", () => {
    const before = renamed();
    expect(applyComponentIdRename(before, "", "a2")).toBe(before);
    expect(applyComponentIdRename(before, "a", "")).toBe(before);
    expect(applyComponentIdRename(before, "a2", "a2")).toBe(before);
  });

  it("refuses to merge references when the new id is not unique", () => {
    const before = doc({
      components: [
        { id: "a2", name: "A", kind: "process" },
        { id: "a2", name: "Dup", kind: "process" },
      ],
      data_flows: [{ id: "f1", from_component: "a", to_component: "a2", name: null }],
    });
    expect(applyComponentIdRename(before, "a", "a2")).toBe(before);
  });

  it("refuses to steal references when another row still holds the old id", () => {
    // Two rows shared the id "a" and one was renamed. Rewriting "a" -> "a2" here would
    // hand the surviving row's flows and assets to the row that was edited.
    const before = doc({
      components: [
        { id: "a2", name: "Edited", kind: "process" },
        { id: "a", name: "Still a", kind: "process" },
      ],
      data_flows: [{ id: "f1", from_component: "a", to_component: "a", name: null }],
    });
    expect(applyComponentIdRename(before, "a", "a2")).toBe(before);
  });

  it("does not touch in_trust_boundary, which names a boundary and not a component", () => {
    const before = doc({
      components: [{ id: "a2", name: "A", kind: "process", in_trust_boundary: "a" }],
      trust_boundaries: [{ id: "a", name: "Boundary literally called a" }],
    });
    const out = applyComponentIdRename(before, "a", "a2");
    expect(out.components[0].in_trust_boundary).toBe("a");
  });
});
