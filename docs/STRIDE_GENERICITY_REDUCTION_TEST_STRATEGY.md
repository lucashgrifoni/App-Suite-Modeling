# Redução de genericidade residual do STRIDE (estratégia de teste)

## Como medir redução de genericidade (objetivo)

Métrica simples, objetiva e comparável (finance + e-commerce):

- Contar, no `report.md`, quantas linhas de item de ameaça contêm identificadores `eng_*` (STRIDE/engine) quando comparando:
  - modo `legacy` (sem supressão)
  - modo `harmonized` (supressão por cluster + categorias)

Evidência automatizada:

- `artifacts/stride-genericity-reduction/summary.json`

## Como medir preservação de rastreabilidade

- Validar que o `analyze.json` continua sendo gerado normalmente pelo CLI (sem modo de view).
- Garantir que o “clean up” é **apenas no Markdown**:
  - o JSON permanece disponível nos artefatos e no pipeline padrão.

Evidências:

- `artifacts/stride-genericity-reduction/analyze/<app>/analyze.json`
- `artifacts/stride-genericity-reduction/{legacy,harmonized}/<app>/analyze.json`

## Como medir melhora de coesão

Critério observável:

- Presença do bloco `### Categorias de risco (top)` no modo `harmonized`.
- Top‑N curto por categoria com `biz_*` liderando onde aplicável.

Evidências:

- `.../harmonized/<app>/report.md`

## Como medir redução de redundância no report.md

Critérios:

- Menos STRIDE `tampering`/`elevation_of_privilege` genéricos em temas já cobertos por famílias `biz_*`.
- “Notas de harmonização” indicando supressão de apresentação (sem apagar rastreabilidade).

## Verificar que o pipeline não regrediu

Executar obrigatoriamente:

- `python -m pytest tests/test_threat_engine.py -q`
- `python scripts/run_test_app_validation.py`

## Testes adicionais criados nesta rodada

- Script de comparação before/after (reprodutível):
  - `python scripts/run_stride_genericity_before_after.py`

## Riscos que permanecem (honestidade técnica)

- A supressão é heurística/semântica controlada, não prova formal de equivalência.
- STRIDE continuará gerando achados genéricos em partes não cobertas por `biz_*`.
- O modo `legacy` continua necessário como referência de rastreabilidade/diagnóstico quando desejado.

