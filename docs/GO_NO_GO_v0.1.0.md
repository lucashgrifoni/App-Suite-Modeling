# Gate GO / NO-GO — v0.1.0

**Uma página.** Usar no dia da publicação. Detalhes operacionais: [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md) · passo a passo: [`PUBLISH_PLAYBOOK.md`](PUBLISH_PLAYBOOK.md).

## Regra de decisão

| Resultado | Condição |
|-----------|----------|
| **GO** | Todos os itens **decisivos** abaixo estão assinalados. |
| **NO-GO** | Falha em **qualquer** item decisivo **ou** bloqueador aberto não aceite por escrito. |

**Não bloqueiam a tag v0.1.0:** limitações documentadas em [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) (MVP sem persistência/auth, heurísticas, consola Windows/Unicode, etc.) — desde que não escondam um defeito **novo** de última hora no branch a publicar.

---

## Checklist decisivo (marcar no dia D)

- [ ] **Escopo da release congelado** — [`RELEASE_SCOPE_FREEZE.md`](RELEASE_SCOPE_FREEZE.md) aceite para esta tag.
- [ ] **Versão `0.1.0` confirmada** em `pyproject.toml` e `apps/web/package.json`.
- [ ] **`CHANGELOG.md`** com entrada `[0.1.0]` coerente com o que se publica.
- [ ] **Release notes** — [`RELEASE_NOTES_v0.1.0.md`](RELEASE_NOTES_v0.1.0.md) prontas para copiar/resumir na release.
- [ ] **Limitações** — [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) lidas; sem promessas novas no README.
- [ ] **README / docs** — alinhados com a realidade ([`README.md`](../README.md), [`docs/README.md`](README.md)).
- [ ] **Suíte Python** — `python -m pytest` na raiz **verde** (última execução no branch a publicar).
- [ ] **Smoke RC** — `tests/test_smoke_release_candidate.py` **verde** nessa execução.
- [ ] **Build UI** — `npm run ci:build` ou `npm run ci:build:portable` **verde**.
- [ ] **E2E smoke UI** — `npm run e2e:smoke` (ou `e2e:smoke:portable` alinhado ao CI) **verde**.
- [ ] **Artefactos** — wheel gerado com `python -m build` quando for anexar (`dist/*.whl` não vai para o git).
- [ ] **CI remoto verde** — workflow em `.github/workflows/ci.yml`: jobs `python`, `web` (Ubuntu + Windows), `web-e2e-smoke` concluídos com sucesso no **commit** que receberá a tag.
- [ ] **Sem bloqueadores abertos** — issues/PRs críticos não resolvidos só se houver **decisão explícita** de aceitar risco.
- [ ] **Pronto para criar a tag `v0.1.0`** — `git tag -l v0.1.0` vazio **ou** política de tag já acordada se existir conflito.

---

## O que já é vs o que falta (tipico)

| Área | Estado típico neste projeto |
|------|-----------------------------|
| Validação **local** (pytest, build UI, E2E) | Já executada; repetir no branch final antes do GO. |
| **CI remoto** | **Único gate externo** obrigatório antes da tag — não substituível por “só local”. |
| PyPI / imagem Docker | **Opcionais** para a existência da tag Git; planejar à parte se aplicável. |

---

## Passo final de tag e publicação (só após GO)

**Não executar** se o checklist acima não estiver completo.

1. **Pré-condição:** último push no branch alvo com **CI verde** (todos os jobs do `ci.yml`).
2. **Tag anotada** (ajustar `origin` ao remoto real):

   ```bash
   git tag -a v0.1.0 -m "App Suite Modeling v0.1.0"
   git push origin v0.1.0
   ```

3. **Release no GitHub/GitLab:** criar release a partir da tag; colar/resumir [`RELEASE_NOTES_v0.1.0.md`](RELEASE_NOTES_v0.1.0.md); anexar wheel se desejado.
4. **PyPI (opcional):** `python -m build` + `twine upload` com credenciais fora do repositório.
5. **Pós-publicação:** smoke rápido (`GET /health`, `otm validate`/`analyze` em `examples/minimal.otm.yaml`) conforme [`PUBLISH_PLAYBOOK.md`](PUBLISH_PLAYBOOK.md) secção 6.
6. **Rollback:** não apagar tags públicas; preferir `v0.1.1` ou marcar release como pre-release + nota — ver [`PUBLISH_PLAYBOOK.md`](PUBLISH_PLAYBOOK.md) secção 7.

---

## Registo do resultado

| Data | Decisão (GO / NO-GO) | Responsável | Notas (ex.: link do run CI) |
|------|----------------------|-------------|----------------------------|
| | | | |
