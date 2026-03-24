# Smoke Validation (Release Candidate)

Validação funcional mínima para garantir prontidão de release incremental.

## Escopo

- CLI básico
- API básico
- análise STRIDE
- análise LINDDUN
- análise PASTA
- análise PLOT4ai
- export principal
- build mínimo de UI

## Como rodar

```bash
python -m pytest tests/test_smoke_release_candidate.py
```

### Build da UI

Linux/macOS:

```bash
cd apps/web
npm ci
npm run ci:build
```

Windows (fallback oficial):

```bash
cd apps/web
npm ci
npm run ci:build:portable
```

## Resultado esperado

- Status code 200 em endpoints principais da API
- CLI com `exit_code == 0` nos fluxos básicos
- Análises retornando metodologia correta e resumo
- Export retornando artefato `analysis_markdown`
- Build UI concluído sem erro (padrão ou portátil)

## Critérios de aprovação

- Todos os smoke tests passam.
- Build UI validado em pelo menos um caminho oficial por ambiente.
- Sem regressão em contratos de análise.
