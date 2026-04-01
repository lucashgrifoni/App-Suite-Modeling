# Decisao Arquitetural - Test Apps de Validacao

## Contexto
Foi solicitada a criacao de 3 apps de teste (Financas, Saude, E-commerce/Assinatura) para validar o projeto sem contaminar o core e sem regressao.

## Decisao
- Codigo executavel dos apps foi colocado em `fixtures/apps/`.
- Modelos de threat modeling foram colocados em `examples/test-apps/`.
- Documentacao formal ficou em `docs/` e `docs/test-apps/`.
- Automacao de execucao ficou em `scripts/run_test_app_validation.py`.
- Evidencias de execucao foram direcionadas para `artifacts/test-app-validation/`.

## Justificativa
- `fixtures/` e `examples/` sao areas naturalmente isoladas para casos de teste e modelos.
- Mantem separacao clara entre:
  - core do produto (`apps/`, `packages/`)
  - massa de validacao (`fixtures/`, `examples/test-apps/`)
  - evidencias (`artifacts/`)
- Rollback e simples: remocao dos novos caminhos nao afeta a arquitetura principal.

## Alternativas avaliadas e descartadas
- **Adicionar em `apps/`:** descartado por risco de acoplamento e poluicao da linha principal.
- **Adicionar em `tests/`:** descartado porque os apps sao fixtures de dominio, nao apenas testes unitarios.
- **Criar novo pacote Python no core:** descartado por aumento desnecessario de complexidade.

## Riscos avaliados
- **Risco de regressao em comandos existentes:** baixo, pois nao houve alteracao de contracts do core.
- **Risco de confusao entre fixture e produto:** mitigado por documentacao explicita de fora de escopo.
- **Risco de crescimento de escopo:** mitigado por escopo minimo e fluxos fechados.

## Impacto esperado
- Positivo: maior capacidade de validacao comparativa entre dominios.
- Negativo potencial: manutencao adicional de fixtures no tempo.
- Impacto tecnico lateral: baixo.

## Estrategia de isolamento
- Nenhuma dependencia nova adicionada.
- Nenhuma alteracao arquitetural em `apps/` ou `packages/` para suportar os fixtures.
- Integracoes externas sempre mockadas.
- Dados de exemplo locais e controlados.

## Estrategia anti-regression
- Validacao por script unico de smoke + `validate` + `analyze` + `report`.
- Evidencias persistidas por app.
- Resultado consolidado em `summary.json`.
- Falhas registradas e tratadas formalmente no relatorio final.
