# Plano de Hardening Analitico do Motor

## Objetivo da rodada
Reduzir genericidade e aumentar especificidade do output para abuso de negocio/fraude economica, preservando estabilidade e sem expandir escopo de produto.

## Hipotese de melhoria
Se adicionarmos heuristicas de correlacao economica e sequenciamento operacional no motor base, os outputs dos fixtures de Financas e E-commerce passarao a explicitar melhor risco de:
- `payment -> entitlement`;
- `webhook replay/idempotencia`;
- `coupon policy abuse`;
- `ownership/context-aware authorization`.

## Areas de analise a fortalecer
- Business logic abuse
- Economic fraud
- State transition inconsistency
- Authorization with business context
- Event ordering misuse

## Criterios de sucesso
- Presenca de achados explicitos `biz_*` nos outputs de dominio relevante.
- Menor dependencia de textos genéricos "rever controles de contexto".
- Recomendacoes acionaveis conectadas a mecanismo (event_id, owner binding, revogacao atomica, policy de cupom).
- Melhor cobertura de risco economico em Financas/E-commerce.

## Criterios de nao-regressao
- `tests/test_threat_engine.py` passando.
- Fluxo completo dos fixtures passando:
  - smoke
  - validate
  - analyze
  - report
- Sem quebra de metodologia escolhida (`stride`, `linddun`, `pasta`).

## Estrategia de validacao
1. Rodar baseline comparativo usando evidencias da rodada anterior documentada.
2. Aplicar mudanca cirurgica no motor.
3. Reexecutar testes do motor.
4. Reexecutar validacao dos 3 fixtures.
5. Comparar before/after por:
   - contagem de heuristicas;
   - presenca de IDs de abuso economico;
   - qualidade de descricoes/recomendacoes.

## Riscos residuais esperados
- Possivel sobregeracao de achados em modelos muito amplos.
- Ainda nao ha classificacao formal adicional no contrato (apenas no conteudo do achado).
- Casos de fraude economica ultra-especificos podem continuar parciais.
