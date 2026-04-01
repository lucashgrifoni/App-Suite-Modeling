# Templates e industry packs

## Arquitetura

### Templates

- **O quê:** ficheiros `.otm.yaml` **válidos** que servem de ponto de partida (estrutura de componentes, fluxos, fronteiras).
- **Onde:** `packages/industry-packs/otm_industry_packs/data/templates/<id>.otm.yaml`
- **Manifesto opcional:** `<id>.meta.json` com título, descrição, `suggested_pack`, categoria, tags, complexidade, metodologia sugerida, etc.
- **Fonte para novos templates:** `otm_industry_packs/catalog/registry_data.py` + `scripts/emit_template_catalog.py` (ver [TEMPLATE_CATALOG.md](TEMPLATE_CATALOG.md)).
- **CLI:** `otm init -t <id>`, `otm templates`, `otm templates list`, `otm templates show <id>`, `otm init --list-templates`

### Industry packs

- **O quê:** YAML declarativo (`PackDefinition`) com:
  - `risk_tuning`: multiplicadores de **likelihood** e **impact** (aplicados às heurísticas base e às ameaças do pack);
  - `additional_threats`: regras STRIDE **complementares** (tipicamente categorias que o motor base não gera para aquele `ComponentKind`, para não duplicar);
  - `control_hints`: texto para relatório / backlog.
- **Onde:** `data/packs/<id>.yaml`
- **Motor:** `ThreatAnalysisEngine().analyze(doc, pack=load_pack("finance"))`
- **CLI:** `otm analyze modelo.otm.yaml --pack finance`, `otm packs`

### Princípio de simplicidade

- Templates = **diagrama inicial**; packs = **contexto de risco** reutilizável.
- Sem DSL própria pesada: tudo é **YAML + Pydantic**.

## Fluxo rápido

```bash
otm templates
otm init -t saas-web -o modelo.otm.yaml
otm validate modelo.otm.yaml
otm analyze modelo.otm.yaml --pack saas
otm report modelo.otm.yaml --pack saas -o REL.md
```

## Packs disponíveis (inicial)

| ID | Setor |
|----|--------|
| `finance` | Finanças |
| `telecom` | Telecom |
| `saas` | SaaS multi-tenant |
| `transport` | Transporte |
| `cloud_native` | Cloud / Kubernetes |

## Catálogo de templates

O catálogo embutido inclui **dezenas** de cenários (aplicações, cloud, identidade, integrações, IA, setores, objetivos). Lista completa e filtros: **API** `GET /v1/templates`, **UI** página Templates, **CLI** `otm templates list`.

Referência rápida: [TEMPLATE_CATALOG.md](TEMPLATE_CATALOG.md).

## Templates legados (exemplos)

| ID | Uso |
|----|-----|
| `saas-web` | Browser → WAF → API → BD |
| `cloud-native` | Ingress → workload → cache → BD |
| `api-backend` | Cliente → API → fila → worker → BD |

Um exemplo cópia está em `examples/example-template-saas-web.otm.yaml`.
