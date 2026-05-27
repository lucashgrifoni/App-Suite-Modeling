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
