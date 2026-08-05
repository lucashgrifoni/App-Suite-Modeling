# Release Notes - RC1 (incremental)

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


## Highlights

- Branding oficial consolidado como **App Suite Modeling**.
- Arquitetura multi-metodologia mantida simples e extensível.
- STRIDE permanece default e mais madura.
- LINDDUN evoluída com camada nativa incremental.
- NIST Data-Centric v1 incremental em andamento.
- PASTA fase 2 e PLOT4ai fase 2 com insights especializados.
- CI com hardening para build UI em Linux/Windows.
- Smoke suite dedicada para validação de release.

## Estado por metodologia

- STRIDE: **Mature**
- LINDDUN: **Evolving**
- NIST Data-Centric: **Evolving**
- OCTAVE Allegro: **Evolving**
- CIA/CIA-DIE: **Evolving**
- PASTA: **Specialized**
- PLOT4ai: **Specialized**

## Limitações conhecidas

- Em alguns ambientes Windows com `&` no caminho do projeto, `npm run build` pode falhar por resolução de wrapper `.cmd`.
- Caminho oficial alternativo documentado: `npm run ci:build:portable`.

## Próximo foco sugerido

- Hardening adicional de release (assinatura/checksum de artefatos e smoke de integração UI↔API em ambiente efêmero).
