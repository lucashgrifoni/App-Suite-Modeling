# Publish Playbook (RC2)

Playbook operacional para publicação incremental controlada de **App Suite Modeling**.

## Pre-release validation

### Pré-requisitos

- Python 3.12+
- Node 20+
- Dependências instaladas (`pip install -e ".[dev,cli,api]"`, `npm ci` em `apps/web`)
- Acesso ao repositório e permissões de release

### Validações obrigatórias

1. CI verde (jobs python + web + smoke).
2. Testes locais:
   - `python -m pytest`
   - `python -m pytest tests/test_smoke_release_candidate.py`
3. UI:
   - Linux/macOS: `npm run ci:build`
   - Windows (path sensível): `npm run ci:build:portable`
4. E2E smoke mínimo UI:
   - `npx playwright install chromium`
   - `npm run e2e:smoke`
5. Docs/release:
   - `CHANGELOG.md` atualizado
   - `docs/RELEASE_NOTES_RC2.md` pronto
   - limitações conhecidas documentadas

## Publish steps

1. Confirmar branch limpa e CI verde.
2. Atualizar versão/tag conforme convenção.
3. Criar tag anotada:
   - `v0.2.0-rc2` (exemplo RC)
4. Publicar release no GitHub com:
   - título da release
   - notas de release
   - highlights e limitações
5. Vincular documentação de release/checklist na descrição.

## Post-release validation

1. Validar página da release publicada.
2. Reexecutar smoke rápido:
   - API health
   - CLI validate/analyze
   - UI smoke E2E mínimo
3. Confirmar links de docs e notas.
4. Abrir issue de acompanhamento com:
   - riscos residuais
   - próximos passos para GA.

## Rollback/mitigação básica

- Se release quebrar smoke crítico:
  1. marcar release como pre-release/problemática no GitHub,
  2. comunicar limitação nas notas,
  3. abrir hotfix branch,
  4. publicar `-rcX+1` com correção mínima.
