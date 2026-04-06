# Pre-commit (opcional)

Ganchos locais alinhados ao CI: **Ruff** (lint + format) em `packages/`, `apps/`, `tests/` e **Mypy parcial** só em `otm_core_schema` + `otm_api` (rápido em máquas de desenvolvimento).

## Instalação

```bash
pip install pre-commit
pre-commit install
```

## Executar manualmente

```bash
pre-commit run --all-files
```

No Windows, se `pre-commit` não estiver no `PATH` após `pip install`, use:

```bash
python -m pre_commit run --all-files
```

## Notas

- O job completo de **Mypy monorepo** continua apenas no **CI**; o pre-commit não substitui o `mypy` alargado.  
- Se não usar pre-commit, nada muda no fluxo obrigatório: `ruff` + `mypy` no GitHub Actions.
