# Relatorio Final - Harmonizacao de Output (STRIDE + biz_*)

## Resumo executivo
Rodada cirúrgica concluída com melhora observável de coesão, priorização por especificidade e deduplicação semântica no relatório Markdown, sem regressão de execução.

Decisão da rodada: **PARTIAL GO**

## Mudancas implementadas
- Arquivo alterado: `packages/exporters/otm_exporters/analysis_markdown.py`
- Melhorias:
  - visão harmonizada de ameaças (`Ameaças sugeridas (harmonizadas)`);
  - priorização com preferência por achados `biz_*`;
  - supressão textual de redundância STRIDE em alvos com `biz_*`;
  - nota explícita de rastreabilidade da deduplicação;
  - recomendações consolidadas por causa raiz.

## Impacto observado
- Finance e E-commerce agora mostram `biz_*` no topo do resumo executivo.
- Relatório passou a explicitar quantos achados genéricos foram ocultados por sobreposição (ex.: 5).
- Recomendações deixam de estar fragmentadas e passam a ser agrupadas por mecanismo corretivo.

## Exemplos de melhora real
- `biz_webhook_replay_economic_abuse` e `biz_payment_entitlement_mismatch` destacados na prioridade imediata.
- `biz_coupon_reuse_and_discount_stacking` aparece como fraude econômica explícita.
- seção `Recomendações consolidadas por causa raiz` agrupa idempotência/owner-binding/cupom/revogação.

## Duplicidades reduzidas
- Sobreposição STRIDE `tampering/elevation_of_privilege` com `biz_*` no mesmo alvo foi reduzida na narrativa principal.
- Rastreabilidade preservada: achados completos seguem no `analyze.json`.

## Genericidades que permaneceram
- A base STRIDE continua ampla por design e ainda aparece em volume considerável.
- A deduplicação atual é heurística por alvo/stride; há casos limítrofes onde redundância parcial pode persistir.

## Regressao detectada?
- Não.
- Evidências:
  - `python -m pytest tests/test_threat_engine.py -q` -> 24 passed
  - `python scripts/run_test_app_validation.py` -> smoke/validate/analyze/report OK nos 3 apps

## Decisao final
- **PARTIAL GO**

Justificativa:
- houve melhora concreta e verificável na coesão e priorização do output;
- porém ainda existe genericidade estrutural da camada STRIDE que requer evolução adicional para chegar em GO pleno.

## Backlog residual
1. Refinar deduplicação por similaridade semântica (não só alvo/stride).
2. Expandir consolidação por causa raiz também para metodologia insights.
3. Ajustar ranking final para separar risco técnico alto de risco econômico material quando scores empatarem.
