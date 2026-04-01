# Validação — Release assets & showcase final (otm-web)

**Data:** 2026-04-01  
**Escopo:** OG image, metadados sociais, guia de screenshots, E2E complementar, copy PT-BR, documentação.

## Comandos automatizados

| Comando | Resultado |
|---------|-----------|
| `npm run ci:build` (`apps/web`) | OK — typecheck + `vite build`; `public/og-image.png` replicada em `dist/og-image.png` |
| `npm run e2e:smoke` | OK — fluxo mínimo home → análise → export |
| `npm run e2e:complement` | OK — tema (data-theme), export com sessão, diff com compare mockado |

## Assets

| Item | Verificação |
|------|-------------|
| `public/og-image.png` | Presente (1200×630); paleta alinhada ao produto (dark / mint) |
| `index.html` | `og:image`, dimensões, `og:image:alt`, `twitter:card` = `summary_large_image`, `twitter:image` |

## Manual (amostra)

| Verificação | Notas |
|-------------|--------|
| Metadados no HTML gerado | `dist/index.html` inclui tags OG/Twitter |
| Dark / light | Toggle altera `data-theme` (coberto no E2E complementar) |
| Showcase | Seguir `docs/SCREENSHOT_GUIDE.md` para estados por ecrã |

## Copy

- Ajustes pontuais PT-BR: *atual* (vs. *actual*), *Selecionado* / *Selecione* (vs. grafia europeia).

## Conclusão

Critérios da fase final atendidos: asset social estático integrado, QA reforçada sem substituir o smoke, build e testes estáveis.
