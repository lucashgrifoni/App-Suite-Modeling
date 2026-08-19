# Playbook de publicação — v0.1.0

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


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

### 7.1 Publicação errada no PyPI

Esta é a única parte do processo que **não se desfaz**, e por isso é a que precisa de estar escrita
antes de ser precisa. O gate de versão
([`scripts/check_release_version_matches_tag.py`](../../../scripts/check_release_version_matches_tag.py))
existe para que este ponto nunca seja alcançado; o que segue é o que fazer se for.

- **Apagar não devolve o número.** Um ficheiro removido do PyPI não pode ser re-carregado com a
  mesma versão. Apagar a release **não** liberta `7.9.0` para uma segunda tentativa — queima-a.
  Portanto a resposta a "publiquei o artefacto errado" nunca é apagar e repetir.
- **A mitigação é `yank`** (PEP 592), não apagar. Uma versão *yanked* deixa de ser escolhida por
  resolvedores, mas continua instalável para quem a fixou explicitamente com `==`. É isso que a
  torna a ferramenta certa: retira a versão do caminho de quem ainda não a apanhou, sem partir
  quem já depende dela.
  ```bash
  # na página do projecto em pypi.org: Manage → Releases → Options → Yank
  # (a razão fica pública; escreva-a a pensar em quem a vai ler num relatório de build)
  ```
- **`yank` não remove os ficheiros.** Continuam descarregáveis por URL directo e por hash. Se o
  problema for **conteúdo indevido no artefacto** — um segredo, dados internos, um caminho pessoal —
  então `yank` **não** é a resposta: trate como divulgação, rode o que foi exposto, e só depois
  trate da versão. Assuma que o artefacto foi espelhado no instante em que ficou público.
- **Sequência normal:** `yank` da versão má → corrigir → nova versão *patch* (nunca reutilizar o
  número) → entrada no `CHANGELOG.md` a dizer o que aconteceu e qual usar → se a versão má chegou a
  ser recomendada em qualquer lado, corrigir também esses sítios.
- **Não corrigir só o PyPI.** A tag Git, a release do GitHub e o `CHANGELOG.md` têm de contar a
  mesma história; uma versão *yanked* que continue a ser a mais recente nas release notes manda as
  pessoas para o sítio errado.
