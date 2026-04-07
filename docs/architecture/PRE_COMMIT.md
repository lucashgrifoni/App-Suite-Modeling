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

### `gitpage/` e `npm ci` no GitHub Pages

O workflow usa **Node 20** (npm **10.x**). Se regenerares `gitpage/package-lock.json` com **npm 11+**, o `npm ci` no Actions pode falhar (entradas em falta no lock, p.ex. **`@emnapi/core` / `@emnapi/runtime`**). Para alinhar:

```bash
cd gitpage && npx npm@10.9.2 install
```

O mesmo alinhamento aplica-se a **`apps/web/`** quando alterares dependências npm (job `web` no CI usa Node 20 + npm 10).
