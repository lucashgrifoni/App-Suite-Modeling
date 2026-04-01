# Como executar validacao dos 3 test apps

## Pre-requisitos
- Python 3.11+
- Dependencias do projeto instaladas (ideal: `pip install -e ".[dev,cli,api]"`)

## Comando unico
```bash
python scripts/run_test_app_validation.py
```

## O que o fluxo faz
1. Executa smoke local de cada fixture de app.
2. Valida o modelo `.otm.yaml` (`validate`).
3. Roda analise (`analyze`) com `--json-out`.
4. Gera relatorio markdown (`report`).
5. Salva evidencias em `artifacts/test-app-validation/<app>/`.

## Artefatos esperados por app
- `smoke.stdout.log`
- `validate.stdout.log`
- `analyze.json`
- `analyze.stdout.log`
- `report.md`
- `report.stdout.log`

## Observacao
Se algum passo falhar, o script continua para os demais apps e registra o erro no resumo final.
