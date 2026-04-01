# Versionamento e tags

Convenção simples para releases incrementais.

## Formato

- RC: `vMAJOR.MINOR.PATCH-rcN`
- Stable: `vMAJOR.MINOR.PATCH`

## Primeira tag estável deste repositório

- **`v0.1.0`** — release incremental séria documentada em [`RELEASE_NOTES_v0.1.0.md`](RELEASE_NOTES_v0.1.0.md) e [`RELEASE_SCOPE_FREEZE.md`](RELEASE_SCOPE_FREEZE.md).

Exemplos adicionais:

- `v0.2.0-rc1`
- `v0.2.0`

## Regras práticas

1. RCs devem apontar para estado estável de validação.
2. Toda tag deve ter release notes correspondentes.
3. Não reutilizar tag existente.
4. Mudanças de comportamento sem quebra -> incrementar `MINOR`.
5. Correções compatíveis -> incrementar `PATCH`.
