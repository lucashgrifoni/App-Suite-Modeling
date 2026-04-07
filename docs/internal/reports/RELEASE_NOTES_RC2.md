# Release Notes - RC2 (publicação incremental controlada)

## Destaques

- Pipeline de release fortalecida com checklist, smoke suite e playbook operacional.
- Smoke E2E mínimo da UI (headless) adicionado para validar caminho feliz real.
- Verificação automática mínima de links internos de documentação.
- Estratégia oficial para build web em Windows com path problemático:
  - `npm run ci:build:portable`

## Status técnico

- Arquitetura principal preservada.
- Sem motores novos.
- Sem expansão de escopo funcional grande.
- Foco em robustez, validação e publicação.

## Limitações conhecidas

- `npm run build` pode falhar em Windows com `&` no path por wrapper `.cmd`.
- Caminho oficial recomendado para esses casos: scripts portáteis.

## Próximo passo sugerido

- Consolidar GA com smoke E2E em ambiente efêmero com API real e validação pós-release automatizada.
