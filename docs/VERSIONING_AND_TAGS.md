# Versionamento e tags

Convenção simples para releases incrementais.

## Formato

- RC: `vMAJOR.MINOR.PATCH-rcN`
- Stable: `vMAJOR.MINOR.PATCH`

Exemplos:

- `v0.2.0-rc1`
- `v0.2.0-rc2`
- `v0.2.0`

## Regras práticas

1. RCs devem apontar para estado estável de validação.
2. Toda tag deve ter release notes correspondentes.
3. Não reutilizar tag existente.
4. Mudanças de comportamento sem quebra -> incrementar `MINOR`.
5. Correções compatíveis -> incrementar `PATCH`.
