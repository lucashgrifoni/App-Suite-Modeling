import { describe, expect, it } from "vitest";
import type { OtmDocument } from "../types/document";
import { hashDocument } from "./documentIdentity";

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

describe("hashDocument", () => {
  it("returns null for no document", () => {
    expect(hashDocument(null)).toBeNull();
  });

  it("is stable across repeated calls on the same document", () => {
    const doc = minimalDoc({ components: [{ id: "api", name: "API", kind: "process" }] });
    const first = hashDocument(doc);
    expect(first).toMatch(/^[0-9a-f]{8}$/);
    expect(hashDocument(doc)).toBe(first);
    expect(hashDocument(structuredClone(doc))).toBe(first);
  });

  it("ignores key insertion order — re-normalising is not a change", () => {
    const a = { id: "api", name: "API", kind: "process" };
    const b = { kind: "process", name: "API", id: "api" };
    expect(hashDocument(minimalDoc({ components: [a] }))).toBe(
      hashDocument(minimalDoc({ components: [b] })),
    );
  });

  it("ignores explicitly-undefined fields, matching JSON.stringify", () => {
    const withUndefined = minimalDoc({
      components: [{ id: "api", name: "API", kind: "process", description: undefined }],
    });
    const without = minimalDoc({ components: [{ id: "api", name: "API", kind: "process" }] });
    expect(hashDocument(withUndefined)).toBe(hashDocument(without));
  });

  it("does not ignore an explicit null — null and absent are different states", () => {
    const withNull = minimalDoc({
      components: [{ id: "api", name: "API", kind: "process", description: null }],
    });
    const without = minimalDoc({ components: [{ id: "api", name: "API", kind: "process" }] });
    expect(hashDocument(withNull)).not.toBe(hashDocument(without));
  });

  it("changes when any part of the document changes", () => {
    const base = minimalDoc({ components: [{ id: "api", name: "API", kind: "process" }] });
    const digests = new Set([
      hashDocument(base),
      hashDocument(minimalDoc({ ...base, metadata: { title: "Other", tags: [] } })),
      hashDocument(minimalDoc({ ...base, components: [{ id: "api2", name: "API", kind: "process" }] })),
      hashDocument(minimalDoc({ ...base, components: [{ id: "api", name: "API", kind: "queue" }] })),
      hashDocument(
        minimalDoc({
          ...base,
          data_flows: [{ id: "f1", from_component: "api", to_component: "api" }],
        }),
      ),
      hashDocument(minimalDoc({ ...base, threats: [{ id: "t1" }] })),
    ]);
    expect(digests.size).toBe(6);
  });

  it("distinguishes array order", () => {
    const one = { id: "a", name: "A", kind: "process" };
    const two = { id: "b", name: "B", kind: "process" };
    expect(hashDocument(minimalDoc({ components: [one, two] }))).not.toBe(
      hashDocument(minimalDoc({ components: [two, one] })),
    );
  });

  it("distinguishes an array from an object with the same rendering", () => {
    expect(hashDocument(minimalDoc({ threats: [[]] }))).not.toBe(
      hashDocument(minimalDoc({ threats: [{}] })),
    );
  });

  it("handles astral characters in free text", () => {
    const grin = hashDocument(minimalDoc({ metadata: { title: "Pagamentos \u{1F600}", tags: [] } }));
    const beam = hashDocument(minimalDoc({ metadata: { title: "Pagamentos \u{1F601}", tags: [] } }));
    const plain = hashDocument(minimalDoc({ metadata: { title: "Pagamentos ", tags: [] } }));
    expect(grin).toMatch(/^[0-9a-f]{8}$/);
    expect(new Set([grin, beam, plain]).size).toBe(3);
  });
});
