# Decisao Tecnica - Hardening do Motor Analitico

## Diagnostico do problema atual
O fluxo operacional ja estava estavel (`smoke -> validate -> analyze -> report`), e os fixtures estavam expondo cenarios de abuso com qualidade suficiente. O gap remanescente era analitico:
- excesso de heuristicas tecnicas genericas por tipo de componente;
- baixa especificidade para fraude economica e abuso de regra de negocio;
- pouca correlacao explicita entre `pagamento`, `owner`, `entitlement`, `cancelamento`, `cupom` e `ordem de eventos`.

## Por que o problema agora estava no motor (e nao nos fixtures)
- Fixtures ja incluem controles e cenarios de abuso (anti-replay, idempotencia, revogacao, policy de cupom).
- Mesmo com esse endurecimento, o output permanecia parcialmente generico (documentado na rodada anterior como `PARTIAL GO`).
- Portanto, o gargalo estava na heuristica de analise e na forma de expressar o risco.

## Dimensoes analiticas endurecidas nesta rodada
- Detecao de abuso de logica de negocio:
  - replay de webhook com beneficio economico;
  - dupla submissao de acao financeira;
  - autorizacao tecnica sem contexto de negocio.
- Fraude economica:
  - mismatch pagamento -> entitlement;
  - reuso/stacking de cupom.
- Inconsistencia de estado:
  - regressao por ordem de eventos;
  - cancelamento sem revogacao de privilegio;
  - saldo vs transacoes confirmadas.

## Alternativas descartadas
- Reescrever pipeline de heuristicas: descartado (alto risco de regressao e escopo).
- Criar nova taxonomia de schema/contrato: descartado (mudanca estrutural ampla).
- Mover logica para metodologia especifica apenas (ex.: so PASTA): descartado, pois os cenarios tambem afetam STRIDE base.

## Risco de regressao
- Baixo a medio:
  - acrescimo de heuristicas pode inflar volume de achados;
  - risco de sobreposicao parcial com heuristicas existentes.

## Estrategia de preservacao de comportamento atual
- Mudanca local e reversivel:
  - novo modulo isolado `business_abuse_heuristics.py`;
  - plug-in unico no `engine.py` apos heuristicas STRIDE existentes.
- Sem alteracao de contrato de `AnalysisResult`.
- Sem alteracao de CLI/API/UI.
- Testes automatizados da suite do motor executados.

## Limites desta rodada
- Nao houve mudanca de schema nem de taxonomia formal persistida no contrato.
- Nao houve aprendizado estatistico; hardening permanece heuristico/deterministico.
- Ainda pode existir genericidade residual em casos economicos muito especificos de dominio.
