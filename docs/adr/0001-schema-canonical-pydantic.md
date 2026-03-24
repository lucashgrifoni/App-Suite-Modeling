# ADR 0001: Schema canônico com Pydantic

## Status

Aceito (MVP).

## Contexto

Precisamos de uma **fonte da verdade** consumida por CLI, API e UI, com validação forte e evolução versionada (`schema_version`).

## Decisão

- Modelar o documento raiz como `ThreatModelDocument` em **Pydantic v2**.
- Serialização primária **YAML** para Threat Modeling as Code (legível em PR).
- Campo de cabeçalho exposto como `model` no arquivo; em Python o atributo é `model_info` para evitar colisão com a API do Pydantic.
- Referências entre entidades validadas em `model_validator` (integridade antes de qualquer análise).

## Consequências

- JSON Schema gerado automaticamente para contratos e tooling.
- Mudanças breaking exigem bump de `schema_version` e migração documentada.
- Linguagens não-Python podem consumir o JSON Schema ou replicar validação; o **comportamento** do motor continua centralizado em Python até haver necessidade de port.
