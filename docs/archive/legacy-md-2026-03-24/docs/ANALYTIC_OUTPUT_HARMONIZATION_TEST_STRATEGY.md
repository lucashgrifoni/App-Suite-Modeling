# Estrategia de Teste - Harmonizacao de Output

## Como medir reducao de genericidade
- Verificar se top achados do resumo executivo inclui `biz_*` quando houver cenário de negócio forte.
- Verificar redução de STRIDE genérico redundante na seção principal de ameaças.

## Como medir deduplicacao util
- Validar presença de `Notas de harmonização` com quantidade de achados ocultados.
- Confirmar que o JSON mantém todos os achados (rastreabilidade preservada).

## Comparacao before/after
- Before: relatório com lista linear de heurísticas.
- After: relatório com:
  - visão harmonizada;
  - destaque por especificidade;
  - recomendações consolidadas por causa raiz.

## Como avaliar coesao do relatorio
- Seções conectadas: resumo executivo -> ameaças harmonizadas -> recomendações consolidadas.
- Menor fragmentação entre risco técnico e risco de negócio.

## Como avaliar priorizacao melhor
- Prioridade imediata deve favorecer achados específicos com impacto econômico.
- Casos como replay/coupon/entitlement mismatch devem aparecer cedo no ranking textual.

## Riscos a observar
- ocultação excessiva de achados técnicos úteis;
- falsa sensação de redução de risco por apenas reduzir visibilidade;
- drift de consistência entre metodologias.

## Validacao executada nesta rodada
- `python -m pytest tests/test_threat_engine.py -q` -> 24 passed
- `python scripts/run_test_app_validation.py` -> 3/3 apps com smoke/validate/analyze/report OK
