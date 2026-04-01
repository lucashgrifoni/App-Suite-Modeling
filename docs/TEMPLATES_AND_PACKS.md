# Templates e industry packs

## Arquitetura

### Templates

- **O quê:** ficheiros `.otm.yaml` **válidos** que servem de ponto de partida (estrutura de componentes, fluxos, fronteiras).
- **Onde:** `packages/industry-packs/otm_industry_packs/data/templates/<id>.otm.yaml`
- **Manifesto opcional:** `<id>.meta.json` com título, descrição e `suggested_pack` (ID do pack recomendado na análise).
- **CLI:** `otm init -t <id>`, `otm templates`, `otm init --list-templates`

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

## Templates disponíveis (inicial)

| ID | Uso |
|----|-----|
| `saas-web` | Browser → WAF → API → BD |
| `cloud-native` | Ingress → workload → cache → BD |
| `api-backend` | Cliente → API → fila → worker → BD |

Um exemplo cópia está em `examples/example-template-saas-web.otm.yaml`.
