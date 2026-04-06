# README raiz, metadados OSS e publicação GitHub

Consolidação de `README_RELEASE_VALIDATION.md` e `README_RELEASE_HANDOFF.md` (higiene docs, 2026-04).

## Âmbito

- `README.md` (raiz), `docs/PRODUCT_POSITIONING.md`, `docs/SCREENSHOT_GUIDE.md`
- `apps/web/index.html` (meta), `apps/web/public/og-image.svg`

## Gates executados (referência)

| Comando | Uso |
|---------|-----|
| `npm run ci:build` em `apps/web` | typecheck + build |
| `npm run e2e:smoke` em `apps/web` | smoke Playwright |

## Decisões

| Tópico | Racional |
|--------|----------|
| README em inglês | Alcance OSS e clareza técnica |
| UI em pt-BR | Mantida; i18n evolui separadamente |
| `og-image.svg` | Entrega imediata; redes que exijam 1200×630 PNG — ver `SCREENSHOT_GUIDE.md` |
| Badge CI | README mantém nota para URL real após publicação (`OWNER/REPO`) |

## Próximos passos (quando for publicar)

1. Capturar PNGs segundo `SCREENSHOT_GUIDE.md` e incorporar no README.
2. Se necessário para crawlers legados, `og-image.png` 1200×630.
3. Adicionar badge de CI com URL definitiva do repositório.

## Estado

Documentação e metadados alinhados ao produto; alterações em `index.html` devem manter build + smoke E2E verdes.
