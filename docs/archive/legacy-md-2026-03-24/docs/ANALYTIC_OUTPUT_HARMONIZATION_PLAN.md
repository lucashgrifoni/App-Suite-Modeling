# Plano - Harmonizacao de Output Analitico

## Objetivo
Melhorar coesão e utilidade do relatório final harmonizando STRIDE base com `biz_*`, reduzindo redundância sem perda de cobertura.

## Hipotese de melhoria
Se o relatório priorizar achados específicos (`biz_*`) e tratar STRIDE genérico como suporte taxonômico, então:
- haverá menos repetição semântica;
- a priorização refletirá melhor impacto econômico/operacional;
- recomendações ficarão mais acionáveis por causa raiz.

## Criterios de sucesso
- seção explícita de ameaças harmonizadas;
- presença de nota de deduplicação com rastreabilidade;
- resumo executivo destacando achados específicos quando aplicável;
- recomendações consolidadas por causa raiz.

## Criterios de nao-regressao
- testes do motor passam;
- fluxo `smoke -> validate -> analyze -> report` permanece estável;
- achados `biz_*` continuam presentes;
- sem quebra de relatórios dos 3 domínios.

## Estrategia before/after
- Before: baseline da rodada anterior (sem harmonização textual).
- After: novos relatórios com:
  - `Ameaças sugeridas (harmonizadas)`;
  - `Notas de harmonização`;
  - `Recomendações consolidadas por causa raiz`.

## Sinais de melhora real
- menor dominância de achados genéricos em prioridade imediata;
- recomendações consolidadas (idempotência, owner-binding, revogação, política de cupom).

## Sinais de falsa melhora
- apenas rearranjo visual sem mudança na prioridade destacada;
- ausência de nota de deduplicação/rastreabilidade;
- sumiço de achados específicos relevantes.
