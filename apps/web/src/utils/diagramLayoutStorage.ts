import type { XYPosition } from "reactflow";
import type { OtmDocument } from "../types/document";

// sessionStorage namespace for the per-tab diagram layout map. Not a secret —
// it is a public identifier inside the browser's per-origin storage.
const STORAGE_NAMESPACE = "otm.web.diagramLayout";

export type DiagramLayoutMap = Record<string, XYPosition>;

/**
 * Identidade do documento a que um layout pertence.
 *
 * O mapa vivia numa única chave `{componentId: posição}`, e `clearDiagramLayout` só é alcançável
 * pelo botão explícito de reposição — nunca ao trocar de modelo. Ids como `user`, `api` e `db` são
 * banais e repetem-se entre modelos, por isso abrir outro documento no mesmo separador colocava os
 * nós onde o modelo anterior, sem relação nenhum, tinha sido arrastado. O diagrama é como alguém
 * lê a arquitetura; mostrá-lo na disposição de outro sistema é uma figura errada, não um detalhe.
 *
 * A chave é o título, e **não** o título mais os ids dos componentes. A primeira versão incluía os
 * ids, e isso trocava um erro por outro: a chave mudaria em cada componente acrescentado ou
 * removido, apagando o layout do utilizador a cada edição — que é justamente quando ele está a
 * arrastar nós. Dois documentos com o mesmo título passam a partilhar um layout; é uma colisão
 * muito mais estreita do que "todos os modelos partilham um só", e não custa nada a quem edita.
 */
export function documentLayoutKey(doc: OtmDocument | null | undefined): string {
  return doc?.metadata?.title ?? "";
}

/** Remove entradas do layout do documento, mantendo o envelope coerente. */
export function removeDiagramLayoutEntries(documentKey: string, componentIds: readonly string[]): void {
  try {
    const cur = loadDiagramLayout(documentKey);
    for (const id of componentIds) delete cur[id];
    sessionStorage.setItem(STORAGE_NAMESPACE, JSON.stringify({ key: documentKey, positions: cur }));
  } catch {
    /* quota */
  }
}

export function loadDiagramLayout(documentKey: string): DiagramLayoutMap {
  try {
    const raw = sessionStorage.getItem(STORAGE_NAMESPACE);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    const stored = parsed as { key?: unknown; positions?: unknown };
    // Chave diferente lê-se como vazio: as posições pertencem ao documento onde foram arrastadas.
    if (stored.key !== documentKey || !stored.positions || typeof stored.positions !== "object") return {};
    const out: DiagramLayoutMap = {};
    for (const [k, v] of Object.entries(stored.positions as Record<string, unknown>)) {
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

export function saveDiagramLayoutPatch(documentKey: string, componentId: string, pos: XYPosition): void {
  try {
    const cur = loadDiagramLayout(documentKey);
    cur[componentId] = pos;
    sessionStorage.setItem(STORAGE_NAMESPACE, JSON.stringify({ key: documentKey, positions: cur }));
  } catch {
    /* quota */
  }
}

export function clearDiagramLayout(): void {
  try {
    sessionStorage.removeItem(STORAGE_NAMESPACE);
  } catch {
    /* ignore */
  }
}
