/**
 * Dragged node positions leaked from one model into the next.
 *
 * The layout lived in ONE flat `{componentId: position}` map under a single sessionStorage key,
 * and `clearDiagramLayout` is only reachable from the explicit "reset layout" button — never on a
 * model change. Component ids like `user`, `api` and `db` are ordinary and shared between models,
 * so opening a different document in the same tab placed its nodes wherever the previous, unrelated
 * model had been dragged. The diagram is how someone reads the architecture; showing it in a layout
 * that belongs to a different system is a wrong picture, not a cosmetic one.
 *
 * The layout is now stored against the document it belongs to, and a mismatched key reads as empty.
 */
import { beforeEach, describe, expect, it } from "vitest";
import {
  clearDiagramLayout,
  documentLayoutKey,
  loadDiagramLayout,
  saveDiagramLayoutPatch,
} from "./diagramLayoutStorage";
import type { OtmDocument } from "../types/document";

function doc(title: string, componentIds: string[]): OtmDocument {
  return {
    model: { schema_version: "1.0.0" },
    metadata: { title, tags: [] },
    components: componentIds.map((id) => ({ id, name: id, kind: "process" })),
    data_flows: [],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  } as unknown as OtmDocument;
}

const PORTAL = doc("Portal", ["user", "api"]);
const BILLING = doc("Faturação", ["user", "api"]);

beforeEach(() => {
  sessionStorage.clear();
});

describe("diagram layout storage", () => {
  it("gives back the positions dragged on the same document", () => {
    const key = documentLayoutKey(PORTAL);
    saveDiagramLayoutPatch(key, "user", { x: 913, y: 707 });

    expect(loadDiagramLayout(key)).toEqual({ user: { x: 913, y: 707 } });
  });

  it("does not hand another document the positions", () => {
    saveDiagramLayoutPatch(documentLayoutKey(PORTAL), "user", { x: 913, y: 707 });

    expect(loadDiagramLayout(documentLayoutKey(BILLING))).toEqual({});
  });

  it("gives two documents different keys even when their component ids match", () => {
    expect(documentLayoutKey(PORTAL)).not.toBe(documentLayoutKey(BILLING));
  });

  it("gives the same document the same key across reloads", () => {
    expect(documentLayoutKey(PORTAL)).toBe(documentLayoutKey(doc("Portal", ["user", "api"])));
  });

  it("keeps the layout when a component is added or removed", () => {
    // A primeira versão da chave incluía os ids dos componentes, e apagava o layout a cada edição
    // — trocava um erro por outro. O teste fixa a propriedade, não a implementação.
    const key = documentLayoutKey(PORTAL);
    saveDiagramLayoutPatch(key, "user", { x: 913, y: 707 });

    const edited = doc("Portal", ["user", "api", "novo"]);

    expect(loadDiagramLayout(documentLayoutKey(edited))).toEqual({ user: { x: 913, y: 707 } });
  });

  it("still clears on request", () => {
    const key = documentLayoutKey(PORTAL);
    saveDiagramLayoutPatch(key, "user", { x: 1, y: 2 });
    clearDiagramLayout();

    expect(loadDiagramLayout(key)).toEqual({});
  });

  it("survives a corrupted store without throwing", () => {
    sessionStorage.setItem("otm.web.diagramLayout", "{not json");

    expect(loadDiagramLayout(documentLayoutKey(PORTAL))).toEqual({});
  });
});
