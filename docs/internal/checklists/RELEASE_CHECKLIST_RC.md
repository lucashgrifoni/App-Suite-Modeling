# Release Candidate Checklist

Checklist técnico para publicação incremental de **App Suite Modeling**.

## 1) Checklist técnico obrigatório

- [ ] Schema canônico valida exemplos e documentos reais
- [ ] CLI funciona (`validate`, `analyze`, `export`, `report`)
- [ ] API responde (`/health`, `/v1/models/*`, `/v1/exports`)
- [ ] UI carrega e executa fluxo mínimo de análise
- [ ] Testes Python passam
- [ ] Smoke suite passa
- [ ] E2E smoke mínimo da UI passa
- [ ] Build da UI validado (padrão ou portátil)
- [ ] Documentação atualizada (README + docs centrais)
- [ ] Branding consistente (nome, identidade, tokens)
- [ ] CHANGELOG atualizado
- [ ] Limitações conhecidas documentadas
- [ ] Frentes de inovação integradas (diff/import/backlog/explainability/plot4ai)

## 2) Comandos de validação rápida

Contratos, snapshots e códigos de erro: ver [CONTRACT_AND_SNAPSHOTS.md](../../features/CONTRACT_AND_SNAPSHOTS.md).

### Python (core/API/CLI/export)

```bash
python scripts/check_core_adapter_boundary.py
python -m pytest
python -m pytest tests/test_smoke_release_candidate.py
```

### UI (Linux/macOS)

```bash
cd apps/web
npm ci
npm run ci:build
```

### UI (Windows com path problemático)

```bash
cd apps/web
npm ci
npm run ci:build:portable
```

### E2E smoke mínimo (headless)

```bash
cd apps/web
npx playwright install chromium
npm run e2e:smoke
```

## 3) Critério de aprovação

Release candidate aprovado quando:

1. Todos os testes passam.
2. Smoke suite passa.
3. Build UI validado por caminho oficial (ou portátil em Windows).
4. Docs e changelog refletem o estado real.
5. Limitações e riscos operacionais estão explícitos.
6. Gate global de regressão verde (`python scripts/run_global_regression_gate.py` na raiz do repositório) antes de etiquetar/subir RC; após mudanças em motor, exportadores ou snapshots, rever ficheiros em `tests/snapshots/` e contratos associados.

## 4) Validação automática de links/docs (escopo e limitação)

Abordagem implementada:
- teste `tests/test_docs_links.py` valida links internos Markdown para ficheiros locais existentes.

Limitações conhecidas:
- não valida disponibilidade de links externos (`http/https`);
- não valida âncoras internas (`#secao`) semanticamente;
- foco intencional em robustez mínima e baixo custo de CI.
