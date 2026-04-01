# Estrategia de Teste - Hardening Analitico do Motor

## Como validar que o motor ficou menos generico
- Verificar se o output adiciona achados especificos de negocio (`biz_*`) com causa e controle concreto.
- Verificar se as descricoes conectam risco a impacto economico/operacional.
- Verificar se aparecem mecanismos de mitigacao especificos:
  - idempotencia por event_id/request_id
  - correlacao owner-payment-entitlement
  - policy de cupom (reuse/stacking)
  - revogacao atomica no cancelamento

## Comparacao before/after
Baseline (rodada anterior documentada):
- Financas: 35 heuristicas
- Saude: 80 heuristicas
- E-commerce: 48 heuristicas
- Ausencia de IDs `biz_*` nos resultados

After (rodada atual):
- Financas: 40 heuristicas
- Saude: 81 heuristicas
- E-commerce: 54 heuristicas
- Presenca de IDs `biz_*` em Financas/E-commerce e `biz_authorization_without_business_context` em Saude

## Fixtures/cenarios usados
- `examples/test-apps/finance-wallet.otm.yaml` (metodologia `stride`)
- `examples/test-apps/health-clinic.otm.yaml` (metodologia `linddun`)
- `examples/test-apps/ecommerce-subscription.otm.yaml` (metodologia `pasta`)

## Sinais de melhora real
- `biz_webhook_replay_economic_abuse`
- `biz_payment_entitlement_mismatch`
- `biz_coupon_reuse_and_discount_stacking`
- `biz_cancel_without_entitlement_revocation`
- `biz_double_submission_financial_action`
- `biz_balance_transaction_inconsistency`

## Sinais de falsa melhora
- Apenas aumento de volume sem novos mecanismos causais.
- Texto maior com mesmos conceitos genéricos.
- Risco economico sem correlacao com owner/entitlement/estado.

## Riscos de regressao a observar
- inflacao de achados com pouco valor;
- perda de clareza de achados tecnicos classicos;
- quebra de consistencia do summary.

## Execucao obrigatoria desta rodada
- `python -m pytest tests/test_threat_engine.py -q` -> **24 passed**
- `python scripts/run_test_app_validation.py` -> **3/3 apps com smoke/validate/analyze/report OK**
