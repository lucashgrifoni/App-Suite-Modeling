# Checklist final de lançamento — v0.1.0

Marque cada item no dia do publish. Um único “não” bloqueia a tag de produção até correção ou nota explícita de exceção.

**Versão enxuta (só decisões):** use [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md).

## Escopo e documentação

- [ ] **Escopo congelado** — [`RELEASE_SCOPE_FREEZE.md`](RELEASE_SCOPE_FREEZE.md) lido e aceite para esta tag.
- [ ] **Versão definida** — `0.1.0` em `pyproject.toml` e `apps/web/package.json` (já alinhados).
- [ ] **CHANGELOG** — entrada `[0.1.0]` publicada; secção `[Unreleased]` pronta para trabalho futuro.
- [ ] **Release notes** — [`RELEASE_NOTES_v0.1.0.md`](RELEASE_NOTES_v0.1.0.md) final.
- [ ] **Limitações** — [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) revisto.
- [ ] **Docs alinhadas** — README raiz + [`docs/README.md`](README.md) coerentes com a realidade.

## Qualidade e CI

- [ ] **CI verde** — pipeline remoto (Python + web + smoke conforme repositório).
- [ ] **Testes Python** — `python -m pytest` na raiz (suíte completa).
- [ ] **Smoke RC** — `tests/test_smoke_release_candidate.py` incluído no resultado verde.
- [ ] **Build UI** — `npm run ci:build` (Linux/macOS) ou `npm run ci:build:portable` (Windows com path problemático).
- [ ] **E2E smoke UI** — `npm run e2e:smoke` em `apps/web` (Chromium instalado).

## Artefactos

- [ ] **Wheel/sdist** — `python -m build` gera `open_threat_model-0.1.0-*.whl` (não commitar `dist/`).
- [ ] **Assets UI** — build de `apps/web` produz `dist/` (ignorado pelo git; anexar à release se desejado).
- [ ] **Docker API** — opcional: `docker build -f apps/api/Dockerfile` conforme o seu registry.

## Segurança e OSS

- [ ] **Sem segredos** — nenhum token/credencial novo no diff.
- [ ] **Postura** — `SECURITY.md` e licença `LICENSE` actuais.

## Tag e publicação

- [ ] **Tag anotada** — `v0.1.0` (ver [`VERSIONING_AND_TAGS.md`](VERSIONING_AND_TAGS.md)).
- [ ] **Release GitHub/GitLab** — notas copiadas ou linkadas para `RELEASE_NOTES_v0.1.0.md`.
- [ ] **PyPI** (se aplicável) — upload do wheel com a mesma versão.

## Pós-publicação

- [ ] **Smoke pós-tag** — health API, `otm validate` + `otm analyze` em exemplo mínimo.
- [ ] **Rollback** — se crítico: marcar release como pre-release, hotfix mínimo, nova tag patch (ver [`PUBLISH_PLAYBOOK.md`](PUBLISH_PLAYBOOK.md)).

## Critério “pronto para lançar”

Todos os itens obrigatórios acima marcados **e** evidência registada (local: [`VALIDATION_REPORT_v0.1.0.md`](VALIDATION_REPORT_v0.1.0.md); CI: logs do pipeline).
