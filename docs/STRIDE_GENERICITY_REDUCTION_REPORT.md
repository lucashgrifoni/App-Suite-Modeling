# Redução de genericidade residual do STRIDE (relatório da rodada)

## Resumo executivo

Objetivo: reduzir a dominância narrativa do STRIDE genérico no `report.md` quando já existir `biz_*` cobrindo a mesma causa raiz, **sem perder rastreabilidade** no `analyze.json`.

Decisão desta rodada: **GO (com riscos residuais leves documentados)**.

## Mudanças implementadas

- **Etapa 1 — Deduplicação semântica por cluster (Markdown)**: supressão conservadora (somente apresentação) de STRIDE `tampering/elevation_of_privilege` quando houver sobreposição temática com famílias `biz_*`.
- **Etapa 2 — Agrupamento por categoria (top‑N)**: adicionado bloco curto `Categorias de risco (top)` para orientar leitura humana sem inflar texto.
- **Etapa 3 — Motor (executada de forma cirúrgica)**: supressão conservadora na origem do ruído, marcando como `skipped_as_duplicate=True` apenas STRIDE `eng_*` em `tampering/elevation_of_privilege` quando há famílias `biz_*` correlatas (rastreável no JSON).

Arquivos alterados:

- `packages/exporters/otm_exporters/analysis_markdown.py`
- `packages/threat-engine/otm_threat_engine/engine.py`
- `scripts/run_stride_genericity_before_after.py` (evidência before/after reproduzível)

## Evidência before/after (finance + e-commerce)

Artefatos gerados:

- `artifacts/stride-genericity-reduction/engine_suppression_{off,on}/{legacy,harmonized}/<app>/report.md`
- `artifacts/stride-genericity-reduction/summary.json`

Métrica objetiva (linhas de item com `eng_*` no report), com matriz Engine×View:

- **finance**
  - engine off + legacy: **35**
  - engine off + harmonized: **28**
  - engine on + legacy: **28**
  - engine on + harmonized: **28**
- **ecommerce-subscription**
  - engine off + legacy: **42**
  - engine off + harmonized: **33**
  - engine on + legacy: **33**
  - engine on + harmonized: **33**

Fonte: `artifacts/stride-genericity-reduction/summary.json`

## Impacto observado por etapa

### Etapa 1 — Deduplicação por cluster

- Melhorou a narrativa quando existe `biz_webhook_*`, `biz_coupon_*`, `biz_payment_entitlement_*`, etc.
- Mantém rastreabilidade: `analyze.json` permanece completo; a supressão ocorre só no `report.md`.

### Etapa 2 — Categorias de risco (top)

- Tornou explícito, em poucos bullets, o que é:
  - risco econômico,
  - abuso de lógica/processo,
  - inconsistência de estado,
  - técnico clássico (STRIDE).

### Etapa 3 — Supressão cirúrgica no motor (sem apagar rastreabilidade)

- Converte parte do ganho da Etapa 1 em **redução na origem** (mesmo no view `legacy`), sem esconder o dado: os itens continuam no `analyze.json` com `skipped_as_duplicate=true`.
- Controle de reversibilidade: `OTM_ENGINE_STRIDE_NOISE_SUPPRESSION=0` desativa a Etapa 3 para comparação/diagnóstico.

## O que melhorou

- `biz_*` aparece mais claramente como “linha mestra” de leitura.
- Menos repetição de STRIDE em temas já cobertos por achados específicos.
- Report mais coeso sem perder STRIDE como taxonomia/backup.

## O que permaneceu genérico (e por quê)

- STRIDE ainda tem achados genéricos em áreas fora do alcance de `biz_*` e em flows estruturais (ex.: atravessar fronteira), o que é esperado e coerente com a natureza heurística.

## Regressões detectadas

- Nenhuma detectada nos testes obrigatórios:
  - `python -m pytest tests/test_threat_engine.py -q`
  - `python scripts/run_test_app_validation.py`
  - `python scripts/run_stride_genericity_before_after.py`

## Backlog residual (não bloqueador)

- Refinar clusters e tokens com base em novos fixtures/domínios (sem virar supressão agressiva).
- Refinar clusters/tokens (motor e/ou markdown) com base em novos domínios, mantendo a supressão conservadora.

## Conclusão (honestidade técnica)

Esta rodada **não elimina** a genericidade estrutural do STRIDE, mas **reduz sua dominância narrativa** quando `biz_*` já explica melhor o risco. O STRIDE permanece como taxonomia de apoio e rastreabilidade no JSON, enquanto o relatório Markdown fica mais útil, coeso e menos repetitivo.

