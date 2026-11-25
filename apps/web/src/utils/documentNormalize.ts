/**
 * Correções pontuais de IDs de componente conhecidos por typo na UI / dados antigos.
 * Mantém referências (fluxos, ativos, fronteiras) coerentes com um único rename.
 */

import type { OtmDocument } from "../types/document";

/** Alinhado a `ENTITY_ID_PATTERN` em `otm_core_schema.entity_id` (só IDs técnicos). */
export const OTM_ENTITY_ID_REGEX = /^\w[\w.-]*$/;

/**
 * Normaliza texto digitado/colado num ID que satisfaz {@link OTM_ENTITY_ID_REGEX}.
 *
 * Deixa o utilizador escrever o nome "de qualquer jeito" (acentos, espaços, símbolos)
 * sem cair no `DOCUMENT_VALIDATION_ERROR` do schema canónico — os campos `name`/`title`
 * humanos continuam livres; só o `id` técnico precisa ser ASCII seguro para Mermaid,
 * nomes de ficheiro e contratos de API.
 *
 * Regras (em ordem):
 * 1. translitera acentos para ASCII (ç→c, ã→a, é→e, …) via decomposição Unicode;
 * 2. troca qualquer caráter fora de `[a-zA-Z0-9_.-]` por `_`;
 * 3. remove `.`/`-` iniciais (o primeiro caráter tem de ser `[a-zA-Z0-9_]`).
 *
 * Mantém string vazia como vazia (estado intermédio de edição), sem forçar conteúdo.
 */
export function sanitizeEntityIdInput(raw: string): string {
  if (typeof raw !== "string" || raw === "") return "";
  const ascii = raw.normalize("NFKD").replaceAll(/[\u0300-\u036f]/g, "");
  const replaced = ascii.replaceAll(/[^\w.-]/g, "_");
  return replaced.replace(/^[.-]+/, "");
}

/** Pares [id errado, id correcto]; aplicados em ordem se o rename for não ambíguo. */
const KNOWN_COMPONENT_ID_TYPOS: ReadonlyArray<readonly [string, string]> = [
  ["worke", "worker"],
];

function mapComponentRef(id: string, from: string, to: string): string {
  return id === from ? to : id;
}

/**
 * Renomeia `from` → `to` em componentes e em todas as referências tipadas no cliente.
 *
 * Só aplica se existir um componente com `from` e **não** existir já um com `to`
 * (evita colisão de IDs).
 */
function renameComponentIdIfUnambiguous(
  doc: OtmDocument,
  from: string,
  to: string,
): OtmDocument {
  const hasFrom = doc.components.some((c) => c.id === from);
  const hasTo = doc.components.some((c) => c.id === to);
  if (!hasFrom || hasTo) return doc;

  return {
    ...doc,
    components: doc.components.map((c) =>
      c.id === from ? { ...c, id: to } : c,
    ),
    data_flows: doc.data_flows.map((f) => ({
      ...f,
      from_component: mapComponentRef(f.from_component, from, to),
      to_component: mapComponentRef(f.to_component, from, to),
    })),
    assets: doc.assets.map((a) => ({
      ...a,
      related_component_ids: a.related_component_ids?.map((id) =>
        mapComponentRef(id, from, to),
      ),
    })),
    trust_boundaries: doc.trust_boundaries.map((tb) => ({
      ...tb,
      member_component_ids: tb.member_component_ids?.map((id) =>
        mapComponentRef(id, from, to),
      ),
      outside_component_ids: tb.outside_component_ids?.map((id) =>
        mapComponentRef(id, from, to),
      ),
    })),
  };
}

/** Aplica {@link KNOWN_COMPONENT_ID_TYPOS} ao documento. */
export function applyKnownComponentIdTypoFixes(doc: OtmDocument): OtmDocument {
  let out = doc;
  for (const [wrong, right] of KNOWN_COMPONENT_ID_TYPOS) {
    out = renameComponentIdIfUnambiguous(out, wrong, right);
  }
  return out;
}

function mapDataFlowRef(id: string, from: string, to: string): string {
  return id === from ? to : id;
}

/** Remove `ids` from an optional id list, dropping the key entirely when it was absent. */
function withoutIds(list: string[] | undefined, ids: ReadonlySet<string>): string[] | undefined {
  if (!list) return list;
  return list.filter((id) => !ids.has(id));
}

/** Does this threat/mitigation point at something that no longer exists? */
function targetsRemoved(entry: unknown, components: ReadonlySet<string>, flows: ReadonlySet<string>): boolean {
  if (typeof entry !== "object" || entry === null) return false;
  const o = entry as Record<string, unknown>;
  const c = o.target_component_id;
  const f = o.target_data_flow_id;
  return (typeof c === "string" && components.has(c)) || (typeof f === "string" && flows.has(f));
}

/**
 * Remove components and cascade to everything that referenced them.
 *
 * Deleting a component without this leaves orphan references behind, and the canonical
 * schema rejects them server-side (`otm_core_schema.document` raises "asset '<id>'
 * references unknown component '<id>'"). Every subsequent validate, analyze, export and
 * report then fails with a 422, the broken document is persisted to sessionStorage so a
 * reload does not help, and no screen in this app can edit `related_component_ids` or
 * `member_component_ids` — so the user cannot repair it and has to discard the model.
 *
 * Flows touching a removed component go too, and references to those flows are cleaned up
 * in the same pass; otherwise removing the component just moves the dangling reference
 * from a component id to a flow id.
 */
export function removeComponents(doc: OtmDocument, componentIds: readonly string[]): OtmDocument {
  const removedComponents = new Set(componentIds);
  if (removedComponents.size === 0) return doc;

  const removedFlows = new Set(
    doc.data_flows
      .filter((f) => removedComponents.has(f.from_component) || removedComponents.has(f.to_component))
      .map((f) => f.id),
  );

  return {
    ...doc,
    components: doc.components.filter((c) => !removedComponents.has(c.id)),
    data_flows: doc.data_flows.filter((f) => !removedFlows.has(f.id)),
    assets: doc.assets.map((a) => ({
      ...a,
      related_component_ids: withoutIds(a.related_component_ids, removedComponents),
      related_data_flow_ids: withoutIds(a.related_data_flow_ids, removedFlows),
    })),
    trust_boundaries: doc.trust_boundaries.map((tb) => ({
      ...tb,
      member_component_ids: withoutIds(tb.member_component_ids, removedComponents),
      outside_component_ids: withoutIds(tb.outside_component_ids, removedComponents),
      crossing_flow_ids: withoutIds(tb.crossing_flow_ids, removedFlows),
    })),
    threats: Array.isArray(doc.threats)
      ? doc.threats.filter((t) => !targetsRemoved(t, removedComponents, removedFlows))
      : doc.threats,
    mitigations: Array.isArray(doc.mitigations)
      ? doc.mitigations.filter((m) => !targetsRemoved(m, removedComponents, removedFlows))
      : doc.mitigations,
  };
}

/**
 * Remove data flows and cascade to the assets, boundaries and threats that referenced them.
 *
 * Same failure mode as {@link removeComponents}: `crossing_flow_ids` and
 * `related_data_flow_ids` left pointing at a deleted flow make the document unvalidatable.
 */
export function removeDataFlows(doc: OtmDocument, flowIds: readonly string[]): OtmDocument {
  const removedFlows = new Set(flowIds);
  if (removedFlows.size === 0) return doc;
  const noComponents = new Set<string>();

  return {
    ...doc,
    data_flows: doc.data_flows.filter((f) => !removedFlows.has(f.id)),
    assets: doc.assets.map((a) => ({
      ...a,
      related_data_flow_ids: withoutIds(a.related_data_flow_ids, removedFlows),
    })),
    trust_boundaries: doc.trust_boundaries.map((tb) => ({
      ...tb,
      crossing_flow_ids: withoutIds(tb.crossing_flow_ids, removedFlows),
    })),
    threats: Array.isArray(doc.threats)
      ? doc.threats.filter((t) => !targetsRemoved(t, noComponents, removedFlows))
      : doc.threats,
    mitigations: Array.isArray(doc.mitigations)
      ? doc.mitigations.filter((m) => !targetsRemoved(m, noComponents, removedFlows))
      : doc.mitigations,
  };
}

/**
 * Quando o utilizador altera o ID de um fluxo no assistente, ativos, fronteiras e ameaças
 * podem continuar a referenciar o ID antigo. Actualiza essas referências de `fromId` → `toId`.
 *
 * Só aplica se existir exactamente um fluxo com `toId` (a linha editada), para não fundir
 * referências quando há IDs duplicados na grelha.
 */
export function applyDataFlowIdRename(doc: OtmDocument, fromId: string, toId: string): OtmDocument {
  if (!fromId || !toId || fromId === toId) return doc;
  const rowsWithToId = doc.data_flows.filter((f) => f.id === toId).length;
  if (rowsWithToId !== 1) return doc;

  return {
    ...doc,
    assets: doc.assets.map((a) => ({
      ...a,
      related_data_flow_ids: a.related_data_flow_ids?.map((fid) =>
        mapDataFlowRef(fid, fromId, toId),
      ),
    })),
    trust_boundaries: doc.trust_boundaries.map((tb) => ({
      ...tb,
      crossing_flow_ids: tb.crossing_flow_ids?.map((fid) => mapDataFlowRef(fid, fromId, toId)),
    })),
    threats: Array.isArray(doc.threats)
      ? doc.threats.map((t) => {
          if (typeof t !== "object" || t === null) return t;
          const o = t as Record<string, unknown>;
          const td = o.target_data_flow_id;
          if (typeof td === "string" && td === fromId) {
            return { ...o, target_data_flow_id: toId };
          }
          return t;
        })
      : doc.threats,
  };
}
