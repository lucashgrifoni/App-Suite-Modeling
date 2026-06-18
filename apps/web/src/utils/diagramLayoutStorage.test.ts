import { describe, expect, it } from "vitest";
import { clearDiagramLayout, loadDiagramLayout, saveDiagramLayoutPatch } from "./diagramLayoutStorage";

const KEY = "otm.web.diagramLayout";

describe("diagramLayoutStorage", () => {
  it("saves and loads a position patch", () => {
    saveDiagramLayoutPatch("api", { x: 10, y: 20 });
    expect(loadDiagramLayout()).toEqual({ api: { x: 10, y: 20 } });
  });

  it("merges successive patches without dropping prior nodes", () => {
    saveDiagramLayoutPatch("a", { x: 1, y: 2 });
    saveDiagramLayoutPatch("b", { x: 3, y: 4 });
    expect(loadDiagramLayout()).toEqual({ a: { x: 1, y: 2 }, b: { x: 3, y: 4 } });
  });

  it("returns {} for malformed JSON and ignores non-numeric coordinates", () => {
    sessionStorage.setItem(KEY, "{ bad");
    expect(loadDiagramLayout()).toEqual({});
    sessionStorage.setItem(KEY, JSON.stringify({ a: { x: "no", y: 1 }, b: { x: 5, y: 6 } }));
    expect(loadDiagramLayout()).toEqual({ b: { x: 5, y: 6 } });
  });

  it("clears the stored layout", () => {
    saveDiagramLayoutPatch("a", { x: 1, y: 2 });
    clearDiagramLayout();
    expect(loadDiagramLayout()).toEqual({});
  });
});
