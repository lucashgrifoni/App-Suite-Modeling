# Redução de genericidade residual do STRIDE (plano)

## Objetivo da rodada

Reduzir a **dominância narrativa** do STRIDE genérico no `report.md` **quando** já existir um achado `biz_*` que cubra a mesma causa raiz/tema de negócio, sem perder rastreabilidade no `analyze.json`.

## Escopo

- Alterações **cirúrgicas** no exporter Markdown (`packages/exporters/otm_exporters/analysis_markdown.py`).
- Evidência before/after controlada para:
  - `fixtures`/modelos `finance`
  - `fixtures`/modelos `ecommerce-subscription`

## Fora de escopo

- Criar novos apps/fixtures.
- Refactor amplo do motor.
- Alterar o schema, OTM, ou o contrato do JSON.
- “Eliminar STRIDE” (não é objetivo).

## Etapa 1 — Deduplicação semântica por cluster (Markdown)

### O que fazer

- Expandir supressão no Markdown de STRIDE genérico (somente `tampering`/`elevation_of_privilege`) quando houver `biz_*` correlato, usando clusters controlados por famílias:
  - `biz_webhook_*`
  - `biz_coupon_*`
  - `biz_payment_entitlement_*`
  - `biz_authorization_*`
  - `biz_balance_*`
  - `biz_cancel_*`

### Critérios de sucesso

- `report.md` com menos repetição STRIDE no mesmo tema (webhook/cupom/entitlement/etc.).
- `analyze.json` sem perdas.
- Before/after reproduzível.

### Critérios de não-regressão

- Pipeline `validate → analyze → report` intacto.
- `biz_*` continua aparecendo e liderando ranking/exec summary.

## Etapa 2 — Agrupar por categoria (top‑N), sem inflar texto

### O que fazer

Adicionar bloco curto antes da lista principal:

- Fraude econômica
- Abuso de processo / lógica de negócio
- Inconsistência de estado
- Técnico clássico (STRIDE)

Regras:

- Top‑N curto por categoria (padrão: 2).
- Sem duplicar excessivamente o mesmo achado.

### Critérios de sucesso

- Leitura mais coesa e rápida.
- `biz_*` guia o entendimento, STRIDE atua como taxonomia de apoio.

## Etapa 3 — Redução na origem do ruído (motor) (opcional)

### Condição para executar

Só executar se Etapas 1 e 2 **não** atingirem o critério central (redução observável de redundância STRIDE no Markdown sem perda de rastreabilidade).

### Possíveis ações (cirúrgicas)

- Redução de duplicação em `ComponentKind.USER` quando previsivelmente redundante.
- “Cap” por alvo quando já existir `biz_*` cobrindo causa raiz no mesmo alvo/tema.

### Exigências extras

- Testes adicionais específicos.
- Before/after detalhado.
- Sem afetar `biz_*` e sem regressão evidente em `health`.

## Estratégia de comparação before/after

- Comparação por matriz (Engine×View), preservando `analyze.json`:
  - Engine supressão **off/on** via `OTM_ENGINE_STRIDE_NOISE_SUPPRESSION`
  - View **legacy/harmonized** via `OTM_MARKDOWN_VIEW_MODE`

Evidências:

- `artifacts/stride-genericity-reduction/engine_suppression_{off,on}/{legacy,harmonized}/<app>/report.md`
- `artifacts/stride-genericity-reduction/summary.json`

## Fixtures prioritários

- `examples/test-apps/finance-wallet.otm.yaml`
- `examples/test-apps/ecommerce-subscription.otm.yaml`

## Sinais de melhora real

- Menos itens STRIDE repetindo “webhook/payment gateway tampering” quando há `biz_webhook_*`.
- Menos itens STRIDE repetindo “cupom/discount tampering” quando há `biz_coupon_*`.
- Categorias “Fraude econômica / Abuso / Estado / Técnico” ficam claras em 1 leitura.

## Sinais de falsa melhora

- Apenas reordenação sem redução.
- Supressão ampla/global (perda de informação útil).
- Report “curto” mas com perda de rastreabilidade (não permitido).

