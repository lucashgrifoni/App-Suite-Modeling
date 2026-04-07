# Playbook de publicação — v0.1.0

Playbook curto para o mantenedor publicar **App Suite Modeling** de forma incremental e controlada.

## 0. Gate obrigatório

1. Preencher [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md). Só existe **GO** se o checklist decisivo (incluindo **CI remoto verde**) estiver completo.
2. **Não criar tag** enquanto o resultado for **NO-GO**, salvo exceção documentada pelo mantenedor.

## 1. Pré-publicação

1. Ler [`../decisions/RELEASE_SCOPE_FREEZE.md`](../decisions/RELEASE_SCOPE_FREEZE.md) e [`KNOWN_LIMITATIONS.md`](../../KNOWN_LIMITATIONS.md).
2. Percorrer [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md) e marcar itens.
3. Garantir branch limpa e **CI remoto verde** (além da validação local em [`VALIDATION_REPORT_v0.1.0.md`](../reports/VALIDATION_REPORT_v0.1.0.md)).
4. Instalar dependências: `pip install -e ".[dev,cli,api]"`, `npm ci` em `apps/web`.

## 2. Criação da tag

1. Confirmar versão **`0.1.0`** em `pyproject.toml` e `apps/web/package.json`.
2. Criar tag anotada na branch de release:

```bash
git tag -a v0.1.0 -m "App Suite Modeling v0.1.0"
git push origin v0.1.0
```

Convenção: ver [`VERSIONING_AND_TAGS.md`](../../VERSIONING_AND_TAGS.md).

## 3. Artefactos

| Artefacto | Comando / local |
|-----------|-----------------|
| Wheel / sdist | `python -m build` → `dist/open_threat_model-0.1.0-*.whl` |
| UI estática | `apps/web`: `npm run ci:build` ou `npm run ci:build:portable` → `apps/web/dist/` |
| Imagem API (opcional) | `docker build -f apps/api/Dockerfile` (contexto conforme o seu fluxo) |

Anexar wheel e notas à release no GitHub/GitLab conforme política do projeto.

## 4. Release notes

1. Copiar ou resumir [`RELEASE_NOTES_v0.1.0.md`](../reports/RELEASE_NOTES_v0.1.0.md) na descrição da release.
2. Incluir link para limitações e para o CHANGELOG.

## 5. Publicação PyPI (opcional)

Se o pacote `open-threat-model` for publicado:

```bash
python -m pip install twine build
python -m build
python -m twine upload dist/*
```

Usar tokens de API com permissão mínima; nunca commitar credenciais.

## 6. Verificação pós-publicação

1. Página da release e tag visíveis no remoto.
2. Smoke rápido:
   - `GET /health` na API (se implantada);
   - `otm validate` / `otm analyze` em `examples/minimal.otm.yaml`;
   - opcional: `npm run e2e:smoke` contra UI local apontando à API.
3. Confirmar que links da documentação na release não estão quebrados.

## 7. Rollback / mitigação

- **Tag errada:** não apague tags públicas; publique `v0.1.1` com correção mínima ou marque a release como **pre-release** e documente o problema.
- **Regressão crítica:** branch hotfix a partir da tag anterior estável, patch, nova tag semver, notas de incidente breves.
