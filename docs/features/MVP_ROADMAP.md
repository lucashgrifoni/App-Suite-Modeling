# Plano de implementação — MVP

Objetivo do MVP: **fluxo ponta a ponta** — escrever/gerar um modelo, validar, rodar análise STRIDE básica, ver diagrama e exportar relatório — com **CLI e API** utilizáveis desde o primeiro marco.

## Fase 0 — Fundação (concluída neste repositório)

- Monorepo com pacotes `core-schema`, stubs de engine/mappings/exporters/diagram, `apps/cli`, `apps/api`, `apps/web` (esqueleto).
- Schema canônico `ThreatModelDocument` + exemplo `examples/minimal.otm.yaml`.
- Testes de carga/validação do core.

## Fase 1 — Core utilizável

- Completar I/O: `validate` CLI; endpoint `/validate` estável; mensagens de erro legíveis.
- JSON Schema publicado (`/schema` ou artefato em CI) para editores e testes de contrato.
- Primeiro exportador: **Markdown** (lista de componentes, fluxos, ameaças).

## Fase 2 — Motor STRIDE mínimo

- `otm_threat_engine`: gerar ameaças por componente/fluxo com categorias STRIDE.
- Score de risco simples (ex.: \(L \times I\) com defaults documentados).
- Sugestão de **trust boundaries** heurística (ex.: tudo fora da VPC vs dentro).

## Fase 3 — API + UI alinhadas

- API: CRUD de documento em memória/arquivo (MVP) ou SQLite opcional.
- Web: wizard mínimo (passos) que produz o **mesmo YAML** validado pelo core.
- React Flow: render a partir de `otm_diagram_engine`.

## Fase 4 — Packs e frameworks

- Um **industry pack** (ex.: `web_saas`) e um mapeamento **OWASP ASVS** mínimo (referências reais em `framework_refs`).
- Export **Mermaid** para diagramas em Git/Markdown.

## Fase 5 — Hardening

- Testes de integração API + CLI nos pipelines.
- Docker Compose: `api` + `web` + documentação de desenvolvimento.

## Critérios de saída do MVP

- [ ] Um repositório de exemplo roda `otm validate` e `pytest` verde.
- [ ] Mesmo arquivo passa pela CLI e pela API sem divergência de validação.
- [ ] Relatório Markdown útil para revisão de time AppSec.
- [ ] UI lista/edita elementos básicos sem lógica STRIDE duplicada no front.

## Pós-MVP (não bloqueante)

- PostgreSQL + SQLAlchemy, RBAC, auditoria, integrações (Jira, SIEM), packs por setor completos.
