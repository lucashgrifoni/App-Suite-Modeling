# Next Phase Recommendations

## O que faz sentido fazer depois
1. **Refino analítico incremental**: reduzir genericidade residual STRIDE com foco em precisão, não volume.
2. **Priorização econômica**: melhorar ranking para fraude repetível e inconsistência material billing-entitlement.
3. **Gate global de regressão**: manter como requisito contínuo antes de release amplo (já aprovado com evidência).
4. **Governança de qualidade**: manter comparação before/after por evidência em cada rodada.

## O que nao faz sentido fazer agora
- criar novos domínios/apps de teste;
- reescrever arquitetura do motor;
- refactor amplo sem hipótese validável;
- expansão de escopo de produto durante fase de maturação analítica.

## Melhorias de maior valor (prioridade)
1. deduplicação semântica mais fina no output final;
2. tuning de score por impacto econômico + explorabilidade;
3. reforço de rastreabilidade entre achado, causa raiz e recomendação consolidada.

## Backlog priorizado
### P1
- Manter e automatizar execução contínua do gate global (CI/local), preservando evidências.
- Ajuste de priorização em achados econômicos críticos.

### P2
- Melhor correlação entre sinais de estado operacional e estado econômico.
- Melhor granularidade de recomendações por família de controle.

### P3
- Evolução opcional de taxonomia analítica (sem quebra de contrato).

## Ordem recomendada de execução futura
1. manter gate global de regressão como rotina pré-release;
2. iterar priorização econômica e agrupamento por categorias;
3. iterar deduplicação/cohesão de output;
4. só depois avaliar expansão de escopo funcional.

## Itens de baixo retorno a evitar
- aumento de volume de texto sem ganho de precisão;
- novos artefatos duplicando conteúdo já consolidado;
- mudanças cosméticas de documentação sem impacto em decisão/execução.
