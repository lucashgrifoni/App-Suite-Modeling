# Estrategia de Testes - Validacao dos Test Apps

## Objetivo
Definir e registrar a estrategia minima de validacao executavel para comprovar:
- integridade dos 3 apps de fixture;
- executabilidade do fluxo de analise do projeto;
- ausencia de regressao tecnica evidente.

## Escopo de testes executados
Para cada app:
1. **Smoke da fixture** (`python fixtures/apps/.../app.py`)
2. **Validacao de schema** (`otm validate`)
3. **Analise de ameacas** (`otm analyze --methodology ... --json-out ...`)
4. **Relatorio de saida** (`otm report --output ...`)

### Hardening cirurgico (rodada final)
Foram adicionadas verificacoes negativas especificas de abuso de logica:
- **Financas:** replay de webhook, dupla submissao, extrato de terceiro, auditoria de bloqueios.
- **Saude:** prontuario/documento sem vinculo, cancelamento por perfil incorreto, notificacao sem excesso de PII.
- **E-commerce:** reuse/stacking de cupom, replay de webhook, consistencia owner/valor pagamento, revogacao de entitlement.

Executado via:
- `python scripts/run_test_app_validation.py`

## Testes nao executados (nesta rodada)
- Build completo da UI web
- E2E browser da UI
- Suite completa de testes preexistentes do projeto
- Typecheck global do repositorio

## Motivo para nao execucao
- Objetivo da rodada foi validar fixtures e fluxo de analise de dominio com baixo impacto.
- Escopo controlado para evitar inflar tempo/risco sem necessidade para este gate especifico.

## Evidencias coletadas
- `artifacts/test-app-validation/summary.json`
- Logs por app:
  - `smoke.stdout.log`
  - `validate.stdout.log`
  - `analyze.stdout.log`
  - `report.stdout.log`
- Artefatos por app:
  - `analyze.json`
  - `report.md`
- Evidencias de abuso bloqueado no comportamento:
  - eventos `*_blocked_*` em `audit_log`/`audit` dos fixtures

## Cobertura minima atingida
- Cobertura de executabilidade dos 3 apps: **100%**
- Cobertura do fluxo de analise (validate/analyze/report): **100%**
- Cobertura de comparabilidade de dominio (financas/saude/ecommerce): **100%**
- Cobertura de cenarios de abuso de negocio priorizados: **atingida no nivel de fixture** (com verificacao em smoke)

## Falhas observadas e tratamento
- Falha inicial de schema por enums invalidos em `.otm.yaml`.
- Tratamento: correcao dos campos para valores canonicos suportados.
- Reexecucao completa concluida com sucesso.

## Limitacoes dos testes
- Nao substitui teste de regressao completo do repositório.
- Nao mede performance, escalabilidade ou robustez operacional real.
- Nao valida UX nem comportamento web end-to-end.
- O motor de analise ainda pode apresentar genericidade parcial para fraude economica profunda.

## Risco residual
- **Baixo para objetivo desta iniciativa** (fixtures + fluxo de analise).
- **Medio para release total do projeto** sem rodada complementar de CI completa (testes globais, build UI e smoke E2E).
- **Medio para risco de fraude avancada**, apesar da melhora objetiva dos cenarios de fixture.
