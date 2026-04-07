# Estrutura da documentação (`/docs`)

Este ficheiro explica **como a pasta `docs/` está organizada** para leitores humanos e para contribuidores. Objetivo: separar o que é **guia de produto** do que é **engenharia interna** ou **histórico operacional**.

---

## Princípios

1. **Raiz de `docs/`** — poucos ficheiros **CORE**: entrada ([`README.md`](README.md)), visão do repo, limitações, versionamento, evidência de CI/segurança, mergulho de produto.  
2. **`features/`** — tudo o que ajuda a **usar** o produto (CLI, API, UI, import, diff, exports, i18n, branding, etc.).  
3. **`architecture/`** — desenho do sistema, ADRs, implantação, contratos com CI, políticas de ferramentas (*pre-commit*, Semgrep, *smoke*).  
4. **`internal/`** — auditorias, relatórios pontuais, logs de execução, decisões de congelamento, checklists de lançamento. **Não** esperado como leitura do utilizador final da CLI/UI.  
5. **`screenshots/`** — activos visuais ou índice de onde os colocar.

---

## Árvore resumida

```text
docs/
├── README.md                      # Índice principal (este hub)
├── DOCUMENTATION_STRUCTURE.md     # Este ficheiro
├── DOCS_REORGANIZATION_REPORT.md  # Relatório da reorganização
├── MONOREPO.md
├── REPOSITORY_LAYOUT.md
├── PROJECT_DEEP_DIVE.md
├── KNOWN_LIMITATIONS.md
├── VERSIONING_AND_TAGS.md
├── CI_AND_SECURITY_EVIDENCE.md
├── features/                      # Documentação pública orientada a produto
├── architecture/                  # ADRs, deploy, contratos CI
│   └── adr/
├── internal/
│   ├── audits/
│   ├── reports/
│   ├── logs/
│   ├── decisions/
│   └── checklists/
└── screenshots/
```

---

## Onde encontrar…

| Procura… | Vá a… |
|-----------|--------|
| Instalar e correr | [`README.md`](../README.md) (raiz) + [`README.md`](README.md) (hub) |
| Referência CLI / API / UI | [`features/CLI.md`](features/CLI.md), [`features/API.md`](features/API.md), [`features/UI.md`](features/UI.md) |
| Metodologias (STRIDE, PLOT4ai, …) | [`features/MULTI_ENGINE_ARCHITECTURE.md`](features/MULTI_ENGINE_ARCHITECTURE.md) |
| Import de artefatos | [`features/ARTIFACT_IMPORT.md`](features/ARTIFACT_IMPORT.md) |
| Limitações e honestidade de produto | [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) |
| ADRs | [`architecture/adr/`](architecture/adr/) |
| Perímetro rede / API | [`architecture/DEPLOYMENT_INVARIANTS.md`](architecture/DEPLOYMENT_INVARIANTS.md) |
| Evidência CI / SAST / SCA | [`CI_AND_SECURITY_EVIDENCE.md`](CI_AND_SECURITY_EVIDENCE.md) |
| Checklist de tag / release | [`internal/checklists/`](internal/checklists/) |
| Auditorias e *scorecards* históricos | [`internal/audits/`](internal/audits/) |

---

## Ligações com o repositório

- **Teste de links:** `tests/test_docs_links.py` percorre `README.md` na raiz e todos os `docs/**/*.md` e falha se um link Markdown relativo não resolver para um ficheiro existente.  
- **Migração de caminhos:** script de apoio em [`scripts/docs_apply_path_migration.py`](../scripts/docs_apply_path_migration.py) (já aplicado; não voltar a correr sem necessidade).

---

*Mantido pelo *maintainer* — actualizar quando novas pastas top-level forem adicionadas sob `docs/`.*
