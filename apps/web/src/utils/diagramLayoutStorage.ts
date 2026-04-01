import type { XYPosition } from "reactflow";

const KEY = "otm.web.diagramLayout";

export type DiagramLayoutMap = Record<string, XYPosition>;

export function loadDiagramLayout(): DiagramLayoutMap {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    const out: DiagramLayoutMap = {};
    for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
      if (v && typeof v === "object" && "x" in v && "y" in v) {
        const p = v as { x: unknown; y: unknown };
        if (typeof p.x === "number" && typeof p.y === "number") out[k] = { x: p.x, y: p.y };
      }
    }
    return out;
  } catch {
    return {};
  }
}

export function saveDiagramLayoutPatch(componentId: string, pos: XYPosition): void {
  try {
    const cur = loadDiagramLayout();
    cur[componentId] = pos;
    sessionStorage.setItem(KEY, JSON.stringify(cur));
  } catch {
    /* quota */
  }
}

export function clearDiagramLayout(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
