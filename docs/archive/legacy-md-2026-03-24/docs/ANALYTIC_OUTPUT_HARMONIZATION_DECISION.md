# Decisao Tecnica - Harmonizacao de Output (STRIDE + biz_*)

## Diagnostico atual
Após o hardening de detecção com `biz_*`, o motor passou a capturar abuso de negócio/fraude econômica, mas o output final ainda apresentava:
- coexistência de achados específicos e genéricos com sobreposição parcial;
- narrativa fragmentada entre bloco STRIDE base e blocos business-aware;
- recomendações repetitivas por mesma causa raiz;
- priorização onde um achado genérico podia competir com um achado mais explicativo.

## Por que o gargalo agora e harmonizacao (nao detecao)
- A detecção já cobre os principais padrões de abuso econômico.
- O problema residual estava na apresentação/priorização do resultado para decisão (release gate), não na ausência de sinal.

## Tipos de duplicidade/genericidade observados
- STRIDE `tampering/elevation_of_privilege` genérico no mesmo alvo de `biz_*` específico.
- recomendações quase equivalentes repetidas em múltiplos achados.
- resumo executivo sem preferência explícita por achado business-specific.

## Abordagem escolhida
- Mudança cirúrgica em uma única camada: `packages/exporters/otm_exporters/analysis_markdown.py`.
- Estratégia:
  1. construir visão harmonizada (não destrutiva) que prioriza especificidade;
  2. ocultar na visão textual apenas redundância semântica previsível;
  3. manter rastreabilidade integral no JSON (nada removido do motor);
  4. consolidar recomendações por causa raiz.

## Alternativas descartadas
- Remover heurísticas STRIDE no motor: descartado (perda de cobertura taxonômica).
- Reclassificar contrato de resultado (`AnalysisResult`): descartado (impacto amplo).
- Reescrever ranking global do motor: descartado (escopo maior e risco de regressão).

## Risco de regressao
- Baixo a médio no relatório:
  - possível ocultar achado genérico útil em alguns cenários limítrofes.
- Mitigação:
  - deduplicação aplicada apenas na visualização Markdown;
  - aviso explícito de quantos achados foram ocultados;
  - JSON mantém total rastreável.

## Limites da rodada
- Não altera schema/contrato.
- Não altera detecção base de STRIDE nem `biz_*`.
- Não resolve toda genericidade intrínseca do bloco STRIDE, apenas harmoniza sua narrativa com `biz_*`.
