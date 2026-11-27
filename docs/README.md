# Documentação — App Suite Modeling

Ponto de entrada único para navegar o `/docs`. O mapa editorial (público vs interno) está em **[`DOCUMENTATION_STRUCTURE.md`](DOCUMENTATION_STRUCTURE.md)**.

**Versão de produto:** `7.10.1` — fonte canónica: [`pyproject.toml`](../pyproject.toml); histórico: [`CHANGELOG.md`](../CHANGELOG.md).

---

## Começar aqui (*Getting started*)

1. Instalação: secção [Comece aqui](#comece-aqui-instalação-resumida) abaixo (ou [`README.md`](../README.md) na raiz, em inglês).  
2. Primeiro modelo: `otm init` ou [`examples/minimal.otm.yaml`](../examples/minimal.otm.yaml).  
3. Fluxo: `otm validate` → `otm analyze` → `otm report` / exports via API.  
4. Limitações honestas: [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).
5. Wiki com referências ao código e aos testes: [OpenWiki](../openwiki/quickstart.md) e [manutenção local](openwiki.md).

### Release e qualidade (mantenedores)

- Congelamento de escopo: [`internal/decisions/RELEASE_SCOPE_FREEZE.md`](internal/decisions/RELEASE_SCOPE_FREEZE.md) · [`internal/decisions/ENGINEERING_CLOSEOUT_SCOPE.md`](internal/decisions/ENGINEERING_CLOSEOUT_SCOPE.md)  
- *Definition of Done:* [`internal/checklists/DEFINITION_OF_DONE.md`](internal/checklists/DEFINITION_OF_DONE.md)  
- Gates técnicos: [`internal/checklists/RELEASE_ENGINEERING_CHECKLIST.md`](internal/checklists/RELEASE_ENGINEERING_CHECKLIST.md)  
- Notas históricas: [`internal/reports/RELEASE_NOTES_v0.1.0.md`](internal/reports/RELEASE_NOTES_v0.1.0.md)  
- GO/NO-GO (marco): [`internal/checklists/GO_NO_GO_v0.1.0.md`](internal/checklists/GO_NO_GO_v0.1.0.md)  
- Dia D: [`internal/checklists/LAUNCH_CHECKLIST.md`](internal/checklists/LAUNCH_CHECKLIST.md)  
- Evidência de validação: [`internal/reports/VALIDATION_REPORT_v0.1.0.md`](internal/reports/VALIDATION_REPORT_v0.1.0.md)  
- Avaliação OSS (GO / caveats): [`internal/reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md`](internal/reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md) · [`internal/reports/FINAL_RELEASE_SCORECARD.md`](internal/reports/FINAL_RELEASE_SCORECARD.md) · [`internal/logs/FINAL_RELEASE_EXECUTION_LOG.md`](internal/logs/FINAL_RELEASE_EXECUTION_LOG.md)

---

## Conceitos centrais (*Core*)

| Documento | Conteúdo |
|-----------|----------|
| [`PROJECT_DEEP_DIVE.md`](PROJECT_DEEP_DIVE.md) | Narrativa longa: produto, fluxos, segurança, glossário |
| [`REPOSITORY_LAYOUT.md`](REPOSITORY_LAYOUT.md) | Camadas e pacotes `otm_*` |
| [`MONOREPO.md`](MONOREPO.md) | Árvore do repo, convenções, packaging |
| [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) | O que o produto **não** promete |
| [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) | Tokens, primitivos, temas, contrastes verificados (WCAG 2.2 AA) |
| [`VERSIONING_AND_TAGS.md`](VERSIONING_AND_TAGS.md) | Versão `7.x`, tags Git, marco `v0.1.0` |
| [`CI_AND_SECURITY_EVIDENCE.md`](CI_AND_SECURITY_EVIDENCE.md) | Gates CI, SAST, SCA, evidência DevSecOps |

---

## Funcionalidades (*Features*)

Guias em **[`features/`](features/)** — superfícies e capacidades de produto.

| Documento | Conteúdo |
|-----------|----------|
| [`features/CLI.md`](features/CLI.md) | Comando `otm` |
| [`features/API.md`](features/API.md) | REST `/v1`, perímetro opcional |
| [`features/UI.md`](features/UI.md) | Fluxos da aplicação web |
| [`features/CHOOSE_METHODOLOGY.md`](features/CHOOSE_METHODOLOGY.md) | Escolher metodologia |
| [`features/MULTI_ENGINE_ARCHITECTURE.md`](features/MULTI_ENGINE_ARCHITECTURE.md) | Matriz multi-metodologia |
| [`features/PLOT4AI_AI_SYSTEM.md`](features/PLOT4AI_AI_SYSTEM.md) | PLOT4ai / sistemas de IA |
| [`features/ARTIFACT_IMPORT.md`](features/ARTIFACT_IMPORT.md) | Import OpenAPI, K8s, Terraform — e os limites de cada um |
| [`features/THREAT_MODEL_DIFF.md`](features/THREAT_MODEL_DIFF.md) | Diff semântico |
| [`features/EXPORTERS.md`](features/EXPORTERS.md) | Formatos de export |
| [`features/PREMIUM_REPORTS.md`](features/PREMIUM_REPORTS.md) | Relatórios premium |
| [`features/REMEDIATION_BACKLOG.md`](features/REMEDIATION_BACKLOG.md) | Backlog de remediação |
| [`features/EXPLAINABILITY.md`](features/EXPLAINABILITY.md) | Explicabilidade estruturada |
| [`features/CONTRACT_AND_SNAPSHOTS.md`](features/CONTRACT_AND_SNAPSHOTS.md) | Contratos e snapshots |
| [`features/I18N.md`](features/I18N.md) | Internacionalização pt-BR / en |
| [`features/SCHEMA_V1.md`](features/SCHEMA_V1.md) | Schema canónico v1 |
| [`features/CORE_ENGINE.md`](features/CORE_ENGINE.md) | Motor de análise |
| [`features/TEMPLATES_AND_PACKS.md`](features/TEMPLATES_AND_PACKS.md) · [`features/TEMPLATE_CATALOG.md`](features/TEMPLATE_CATALOG.md) | Templates e *packs* |
| [`features/MVP_ROADMAP.md`](features/MVP_ROADMAP.md) | **Histórico**: o plano que levou ao MVP (fases entregues) |
| [`features/PRODUCT_POSITIONING.md`](features/PRODUCT_POSITIONING.md) | Posicionamento |
| [`features/BRANDING.md`](features/BRANDING.md) | Identidade visual |
| [`features/SCREENSHOT_GUIDE.md`](features/SCREENSHOT_GUIDE.md) | Capturas para README/marketing |
| [`features/MODELING_QUALITY.md`](features/MODELING_QUALITY.md) | Qualidade de modelagem |
| [`features/SECURITY_HEADERS.md`](features/SECURITY_HEADERS.md) | CSP / cabeçalhos da web |

---

## Arquitetura (*Architecture*)

| Documento | Conteúdo |
|-----------|----------|
| [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | Visão técnica |
| [`architecture/adr/`](architecture/adr/) | Architecture Decision Records |
| [`architecture/THREAT_MODEL.md`](architecture/THREAT_MODEL.md) | Threat model do próprio produto (STRIDE, LINDDUN, abuse cases) |
| [`architecture/DEPLOYMENT_INVARIANTS.md`](architecture/DEPLOYMENT_INVARIANTS.md) | Implantação e perímetro |
| [`architecture/CONTRACTS_CI_HYBRID.md`](architecture/CONTRACTS_CI_HYBRID.md) | Contratos, CI, E2E híbrido |
| [`architecture/SMOKE_VALIDATION.md`](architecture/SMOKE_VALIDATION.md) | Smoke / critérios |
| [`architecture/PRE_COMMIT.md`](architecture/PRE_COMMIT.md) | *Pre-commit* opcional |
| [`architecture/SEMGREP_POLICY.md`](architecture/SEMGREP_POLICY.md) | Política Semgrep |
| [`architecture/DESIGN_SYSTEM_FOUNDATION.md`](architecture/DESIGN_SYSTEM_FOUNDATION.md) | Design system (UI) |

---

## Documentação interna (*Internal — mantenedores*)

Material **operacional** (auditorias, relatórios de execução, checklists de lançamento). Não é necessário para uso quotidiano da CLI/API/UI; é útil para *release engineering* e histórico.

**Não apagar links antigos do Git:** entradas no `CHANGELOG` podem ainda mencionar caminhos antigos; o estado actual está aqui e em [`DOCS_REORGANIZATION_REPORT.md`](DOCS_REORGANIZATION_REPORT.md).

### `internal/audits/`

Auditorias e *scorecards* de engenharia (ex.: conformidade, cobertura, achados).

### `internal/reports/`

Relatórios de validação, notas de release, remediação, histórico de UI, metadados GitHub, avaliação GO/NO-GO.

### `internal/logs/`

Logs de execução de ferramentas e da rodada de release.

### `internal/decisions/`

Congelamento de escopo, gates E2E, decisões STRIDE/PLOT4ai, recomendações de fase.

### `internal/checklists/`

Checklists de publicação, RC, *prepublish*, playbooks.

---

## Guia mínimo (primeiro uso)

1. [`README.md`](../README.md) (raiz) — *quick start* e requisitos (Python 3.11+, Node 20+ para UI).  
2. `python scripts/setup_dev.py` — *bootstrap* recomendado.  
3. `otm validate` / `otm analyze` / `otm report` como em [`features/CLI.md`](features/CLI.md).  
4. Metodologia: [`features/CHOOSE_METHODOLOGY.md`](features/CHOOSE_METHODOLOGY.md) ou `otm recommend-methodology`.  
5. Import: [`features/ARTIFACT_IMPORT.md`](features/ARTIFACT_IMPORT.md).  
6. Diff: [`features/THREAT_MODEL_DIFF.md`](features/THREAT_MODEL_DIFF.md).  
7. Backlog: [`features/REMEDIATION_BACKLOG.md`](features/REMEDIATION_BACKLOG.md).

### Comece aqui (instalação resumida)

Use Python 3.11 ou mais recente. Para experimentar a ferramenta sem clonar o repositório, execute em um diretório novo:

```bash
python -m pip install open-threat-model
otm init my-model.otm.yaml --template saas-web
otm validate my-model.otm.yaml
otm analyze my-model.otm.yaml --methodology stride
otm report my-model.otm.yaml -o risk-report.md
```

Revise o rascunho e as ameaças sugeridas antes de usar o relatório em uma decisão.

Para contribuir ou rodar a aplicação web a partir de um clone, siga a [instalação para desenvolvimento](../README.md#quick-start).

---

## Mais referências

| Documento | Conteúdo |
|-----------|----------|
| [`internal/checklists/RELEASE_CHECKLIST_RC.md`](internal/checklists/RELEASE_CHECKLIST_RC.md) | Checklist RC |
| [`internal/checklists/PREPUBLISH_CHECKLIST.md`](internal/checklists/PREPUBLISH_CHECKLIST.md) | *Prepublish* |
| [`internal/checklists/PUBLISH_PLAYBOOK.md`](internal/checklists/PUBLISH_PLAYBOOK.md) | Playbook de tag/release |
| [`internal/reports/RELEASE_NOTES_RC1.md`](internal/reports/RELEASE_NOTES_RC1.md) · [`internal/reports/RELEASE_NOTES_RC2.md`](internal/reports/RELEASE_NOTES_RC2.md) | Notas RC |
| [`internal/reports/GITHUB_README_AND_METADATA.md`](internal/reports/GITHUB_README_AND_METADATA.md) | Metadados OSS |
| [`internal/reports/FRONTEND_UI_ROLLOUT_HISTORY.md`](internal/reports/FRONTEND_UI_ROLLOUT_HISTORY.md) | Histórico da UI |
| [`screenshots/README.md`](screenshots/README.md) | Onde guardar PNGs |

---

## ADR (decisões)

- [`architecture/adr/0001-schema-canonical-pydantic.md`](architecture/adr/0001-schema-canonical-pydantic.md)  
- [`architecture/adr/0002-schema-v1-entities.md`](architecture/adr/0002-schema-v1-entities.md)
