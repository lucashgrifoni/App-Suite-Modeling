# Residual Risk Register

| Risco residual | Categoria | Impacto | Probabilidade | Área afetada | Bloqueador? | Mitigação atual | Mitigação futura recomendada | Decisão |
|---|---|---|---|---|---|---|---|---|
| Genericidade residual leve da camada STRIDE base em parte dos achados | Qualidade analítica | Baixo-Médio | Médio | Motor / relatórios | Não | Camada `biz_*` + harmonização de saída (prioriza achados específicos no relatório) | Refinar deduplicação/ranking incremental por domínio | Aceitar / reduzir depois |
| Priorização econômica ainda não ótima em alguns cenários de fraude muito específicos | Priorização de risco | Baixo-Médio | Baixo-Médio | Motor analítico | Não | Heurísticas business-aware adicionadas + recomendações consolidadas | Ajustar ponderação por impacto econômico e repetibilidade (incremental) | Reduzir depois |
| Gate global de regressão depende de ambiente (Windows + Node) e pode falhar por variação operacional | Governança de release | Baixo | Médio | Release global | Não | Gate automatizado em `scripts/run_global_regression_gate.py` com evidência em `artifacts/global-regression-gate/20260325T121811Z/summary.json` | Manter gate na rotina e capturar logs como requisito de release | Aceitar |
| Dependência de heurísticas determinísticas para cenários de negócio muito específicos | Cobertura analítica | Médio | Baixo-Médio | Motor | Não | Cobertura atual por padrões críticos | Evoluir regras orientadas a contexto de domínio prioritário | Aceitar temporariamente |
| Risco de interpretação excessivamente otimista sem leitura do risco residual documentado | Governança / comunicação | Médio | Baixo | Decisão executiva | Não | Documentação explícita de PARTIAL GO | Exigir checklist de leitura executiva antes de publish/release | Aceitar |

## Nota
Não foi identificado risco residual classificado como bloqueador crítico para continuidade incremental desta fase.
