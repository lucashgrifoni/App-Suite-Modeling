/**
 * Edições de grelha do assistente: cunhar IDs novos e propagar o rename de um componente.
 *
 * Complementa `documentNormalize`, que trata das remoções em cascata. Aqui ficam as duas
 * operações inversas — acrescentar uma linha e renomear uma existente — porque ambas
 * conseguem partir o documento de formas que o utilizador não tem como reparar na UI.
 */

import type { OtmDocument } from "../types/document";

/**
 * Devolve o menor `prefix<n>` (n >= 1) que ainda não está ocupado.
 *
 * O assistente cunhava `comp_${components.length + 1}`. O comprimento do array não é um
 * contador monotónico: acrescentar dois componentes, apagar o primeiro e acrescentar outro
 * dá comprimento 1 e portanto `comp_2` — que é exactamente o ID da linha que sobreviveu.
 * O resultado são dois IDs iguais, chaves React duplicadas na mesma grelha (edições podem
 * cair na linha errada) e um 422 do schema canónico, `duplicate id in components`, ao
 * avançar. Contar contra o conjunto de IDs em uso não tem esse buraco.
 *
 * Reaproveitar um número libertado por uma remoção é seguro: `removeComponents` /
 * `removeDataFlows` já apagaram todas as referências ao ID antigo.
 */
export function nextEntityId(prefix: string, takenIds: readonly string[]): string {
  const taken = new Set(takenIds);
  let n = 1;
  while (taken.has(`${prefix}${n}`)) n += 1;
  return `${prefix}${n}`;
}

function mapComponentRef(id: string, from: string, to: string): string {
  return id === from ? to : id;
}

/** Reescreve `target_component_id` em ameaças, preservando entradas de outra forma. */
function retargetThreats(threats: unknown[], from: string, to: string): unknown[] {
  return threats.map((t) => {
    if (typeof t !== "object" || t === null) return t;
    const o = t as Record<string, unknown>;
    const target = o.target_component_id;
    if (typeof target === "string" && target === from) {
      return { ...o, target_component_id: to };
    }
    return t;
  });
}

/**
 * Quando o utilizador corrige o ID de um componente no assistente, fluxos, ativos,
 * fronteiras e ameaças continuam a apontar para o ID antigo. Actualiza essas referências.
 *
 * Sem isto, corrigir um typo no campo que existe precisamente para isso desliga em silêncio
 * todos os fluxos que partiam desse componente: o servidor responde
 * `data_flow '<id>' from_component '<antigo>' not found` e nenhum ecrã desta aplicação
 * consegue editar `related_component_ids` nem `member_component_ids`, por isso o utilizador
 * não tem como reparar o documento. O campo de ID de fluxo já faz esta manutenção
 * (`applyDataFlowIdRename`); esta é a metade que faltava.
 *
 * Espera que a linha editada já tenha o ID novo (é o que o `onChange` escreve); só trata
 * das referências. Guardas, todas conservadoras:
 *  - exactamente um componente com `toId` — senão o rename fundia referências de duas linhas;
 *  - nenhum componente ainda com `fromId` — senão roubava as referências da linha que ficou.
 *
 * `components[].in_trust_boundary` fica de fora de propósito: nomeia uma fronteira, não um
 * componente, e reescrevê-lo partiria o modelo quando uma fronteira tem o ID antigo.
 */
export function applyComponentIdRename(doc: OtmDocument, fromId: string, toId: string): OtmDocument {
  if (!fromId || !toId || fromId === toId) return doc;
  if (doc.components.filter((c) => c.id === toId).length !== 1) return doc;
  if (doc.components.some((c) => c.id === fromId)) return doc;

  return {
    ...doc,
    data_flows: doc.data_flows.map((f) => ({
      ...f,
      from_component: mapComponentRef(f.from_component, fromId, toId),
      to_component: mapComponentRef(f.to_component, fromId, toId),
    })),
    assets: doc.assets.map((a) => ({
      ...a,
      related_component_ids: a.related_component_ids?.map((id) =>
        mapComponentRef(id, fromId, toId),
      ),
    })),
    trust_boundaries: doc.trust_boundaries.map((tb) => ({
      ...tb,
      member_component_ids: tb.member_component_ids?.map((id) =>
        mapComponentRef(id, fromId, toId),
      ),
      outside_component_ids: tb.outside_component_ids?.map((id) =>
        mapComponentRef(id, fromId, toId),
      ),
    })),
    threats: Array.isArray(doc.threats) ? retargetThreats(doc.threats, fromId, toId) : doc.threats,
  };
}
