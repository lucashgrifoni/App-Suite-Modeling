# Checklist rápido pré-publish (dia D)

Versão curta; decisão GO/NO-GO: [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md); detalhe: [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md).

- [ ] Gate [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md) = GO
- [ ] CI verde (Python + web + smoke)
- [ ] `python -m pytest` na raiz
- [ ] Smoke RC incluído no verde
- [ ] `npm run e2e:smoke` em `apps/web`
- [ ] Build web (`ci:build` ou `ci:build:portable`)
- [ ] `CHANGELOG` com `[0.1.0]`
- [ ] [`RELEASE_NOTES_v0.1.0.md`](RELEASE_NOTES_v0.1.0.md) e [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) ok
- [ ] Tag `v0.1.0` e [`PUBLISH_PLAYBOOK.md`](PUBLISH_PLAYBOOK.md) seguidos
