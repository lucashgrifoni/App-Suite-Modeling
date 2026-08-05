# Release notes — v0.1.0

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**App Suite Modeling** — primeira release pública incremental coordenada após ciclos de hardening e RC documentados.

## Resumo

Esta versão consolida o núcleo **Threat Modeling as Code** com CLI, API e UI alinhadas ao mesmo schema, com multi-metodologia, import de artefatos, diff, backlog e explainability, sem prometer funcionalidades que o repositório não entrega.

## Destaques

- **STRIDE** como default maduro; **LINDDUN** e outras lentes em evolução contínua.
- **PASTA** e **PLOT4ai** em fase 2 especializada (heurísticas e calibração com fixtures realistas).
- **Importadores** para OpenAPI, Terraform, Kubernetes e Helm (conforme documentado).
- **Diff** semântico de modelos e de análises; **backlog** de remediação sugerida.
- **Explainability** integrada ao pipeline de análise.
- **Validação:** suíte pytest extensa, smoke RC, build web (incl. caminho portátil Windows), E2E smoke mínimo (Playwright).

## Artefactos

- Pacote Python: `open-threat-model==0.1.0` (wheel/sdist via `python -m build`).
- UI: build de produção em `apps/web` (`npm run ci:build` ou `ci:build:portable`).
- API: `Dockerfile` em `apps/api/Dockerfile` para empacotamento opcional.

## Limitações conhecidas

Ver [`KNOWN_LIMITATIONS.md`](../../KNOWN_LIMITATIONS.md). Em síntese: sem persistência server-side, sem auth nativa, heurísticas sujeitas a revisão humana, restrições de consola Unicode em alguns terminais Windows.

## Compatibilidade

- Clientes da API devem tratar respostas como JSON evolutivo em `/v1/` dentro de `0.x`.
- Modelos `.otm.yaml` válidos na v0.1.0 devem continuar válidos em patches `0.1.z` salvo correção de bug de validação documentada.

## Créditos

Contribuidores e mantenedores listados no repositório; licença MIT.
