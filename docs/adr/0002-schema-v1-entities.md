# ADR 0002: Schema canônico v1 — entidades e campos

## Status

Aceito.

## Contexto

O MVP precisa de um único documento serializável que cubra metadados, negócio, arquitetura, risco, tratamento, frameworks e evidências — sem duplicar modelos entre CLI, API e UI.

## Decisão

- **`system_type`** e **`industry_sector`** como classificação principal (substitui o antigo `system_profile` único).
- **Ativos** explícitos com ligação a componentes; ameaças podem referenciar ativo.
- **Tratamento** em duas camadas: `TreatmentStatus` na ameaça e `MitigationStatus` na mitigação.
- **Evidências** como catálogo `evidence_suggestions` + referências por ameaça.
- **`metadata` dict** nas entidades para extensão sem alterar o schema em cada pedido de feature.

## Consequências

- YAML legado com apenas `system_profile` deve ser migrado para `industry_sector` / `system_type`.
- Documentação humana: [`SCHEMA_V1.md`](../SCHEMA_V1.md).
