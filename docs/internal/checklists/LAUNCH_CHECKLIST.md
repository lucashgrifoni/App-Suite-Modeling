# Checklist final de lançamento — v0.1.0

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


Marque cada item no dia do publish. Um único “não” bloqueia a tag de produção até correção ou nota explícita de exceção.

**Gates de engenharia (comandos):** [`RELEASE_ENGINEERING_CHECKLIST.md`](RELEASE_ENGINEERING_CHECKLIST.md) — typecheck, build web, pytest, `contracts:verify`, `e2e:critical`, `e2e:hybrid`, etc.

**Versão enxuta (só decisões):** use [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md) (confirmar número em `pyproject.toml` / `apps/web/package.json`; hoje **`7.0.0`**).

## Escopo e documentação

- [ ] **Escopo congelado** — [`../decisions/RELEASE_SCOPE_FREEZE.md`](../decisions/RELEASE_SCOPE_FREEZE.md) lido e aceite para esta tag.
- [ ] **Versão definida** — mesma versão em `pyproject.toml` e `apps/web/package.json` (ex.: `7.0.0`).
- [ ] **CHANGELOG** — entrada da versão a publicar (ex. `[7.0.0]`) coerente; secção `[Unreleased]` pronta para trabalho futuro.
- [ ] **Release notes** — [`RELEASE_NOTES_v0.1.0.md`](../reports/RELEASE_NOTES_v0.1.0.md) final.
- [ ] **Limitações** — [`KNOWN_LIMITATIONS.md`](../../KNOWN_LIMITATIONS.md) revisto.
- [ ] **Docs alinhadas** — README raiz + [`docs/README.md`](../../README.md) coerentes com a realidade.

## Qualidade e CI

- [ ] **CI verde** — pipeline remoto (Python + web + smoke conforme repositório).
- [ ] **Testes Python** — `python -m pytest` na raiz (suíte completa).
- [ ] **Smoke RC** — `tests/test_smoke_release_candidate.py` incluído no resultado verde.
- [ ] **Build UI** — `npm run ci:build` (Linux/macOS) ou `npm run ci:build:portable` (Windows com path problemático).
- [ ] **E2E smoke UI** — `npm run e2e:smoke` em `apps/web` (Chromium instalado).

## Artefactos

- [ ] **Wheel/sdist** — `python -m build` gera `open_threat_model-<versão>-*.whl` (não commitar `dist/`).
- [ ] **Assets UI** — build de `apps/web` produz `dist/` (ignorado pelo git; anexar à release se desejado).
- [ ] **Docker API** — opcional: `docker build -f apps/api/Dockerfile` conforme o seu registry.

## Segurança e OSS

- [ ] **Sem segredos** — nenhum token/credencial novo no diff.
- [ ] **Postura** — `SECURITY.md` e licença `LICENSE` actuais.

## Tag e publicação

- [ ] **Tag anotada** — alinhada à versão (ex. `v7.0.0`) (ver [`VERSIONING_AND_TAGS.md`](../../VERSIONING_AND_TAGS.md)).
- [ ] **Release GitHub/GitLab** — notas copiadas ou linkadas para `RELEASE_NOTES_v0.1.0.md`.
- [ ] **PyPI** (se aplicável) — upload do wheel com a mesma versão.

## Pós-publicação

- [ ] **Smoke pós-tag** — health API, `otm validate` + `otm analyze` em exemplo mínimo.
- [ ] **Rollback** — se crítico: marcar release como pre-release, hotfix mínimo, nova tag patch (ver [`PUBLISH_PLAYBOOK.md`](PUBLISH_PLAYBOOK.md)).

## Critério “pronto para lançar”

Todos os itens obrigatórios acima marcados **e** evidência registada (local: [`VALIDATION_REPORT_v0.1.0.md`](../reports/VALIDATION_REPORT_v0.1.0.md); CI: logs do pipeline).
