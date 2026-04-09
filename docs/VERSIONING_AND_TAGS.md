# Versionamento e tags

Convenção simples para releases incrementais.

## Alinhamento `pyproject.toml` / tags Git

- O campo **`project.version`** em `pyproject.toml` (e `apps/web/package.json`) é a **versão de produto** actual da linha **7.x** (ex.: `7.2.0`).
- Documentos históricos referem **`v0.1.0`** como **marco inicial** congelado ([`RELEASE_NOTES_v0.1.0.md`](internal/reports/RELEASE_NOTES_v0.1.0.md)); não contradizem a linha 7.x — são camadas diferentes de nomenclatura (marco vs. versão de pacote).
- Para uma release pública, alinhar **tag Git** (ex.: `v7.2.0`) com o valor em `pyproject.toml` e uma entrada em [`CHANGELOG.md`](../CHANGELOG.md).

## Formato

- RC: `vMAJOR.MINOR.PATCH-rcN`
- Stable: `vMAJOR.MINOR.PATCH`

## Marco inicial documentado neste repositório

- **`v0.1.0`** — marco documentado em [`RELEASE_NOTES_v0.1.0.md`](internal/reports/RELEASE_NOTES_v0.1.0.md) e [`RELEASE_SCOPE_FREEZE.md`](internal/decisions/RELEASE_SCOPE_FREEZE.md) (contexto de congelamento de escopo).

Exemplos adicionais de tags semânticas:

- `v7.3.0-rc1`
- `v7.3.0`
- `v.7.4` (product line tag aligned with `7.4.0` in `pyproject.toml`)
- `v.7.5` (product line tag aligned with `7.5.0` in `pyproject.toml`)

## Regras práticas

1. RCs devem apontar para estado estável de validação.
2. Toda tag deve ter release notes correspondentes.
3. Não reutilizar tag existente.
4. Mudanças de comportamento sem quebra -> incrementar `MINOR`.
5. Correções compatíveis -> incrementar `PATCH`.
