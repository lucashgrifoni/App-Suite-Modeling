# Handoff — Release assets & showcase final (otm-web)

## Resumo executivo

Fechamento orientado a **showcase e publicação**: imagem **OG estática** (identidade dark/mint), metadados Open Graph/Twitter atualizados, **guia de screenshots** com estados ideais por ecrã, **testes E2E complementares** (tema, export, diff com API mockada), revisão mínima de **copy PT-BR**, sem redesign nem dependências novas.

## Ficheiros criados

- `apps/web/public/og-image.png` — preview social 1200×630  
- `apps/web/e2e/release.spec.ts` — QA complementar  
- `docs/FRONTEND_FINAL_RELEASE_ASSETS_PLAN.md`  
- `docs/FRONTEND_FINAL_RELEASE_ASSETS_VALIDATION.md`  
- `docs/FRONTEND_FINAL_RELEASE_ASSETS_HANDOFF.md` (este ficheiro)

## Ficheiros alterados

- `apps/web/index.html` — `og:image`, dimensões, `og:image:alt`, Twitter `summary_large_image` + `twitter:image`  
- `apps/web/package.json` — script `e2e:complement`  
- `docs/SCREENSHOT_GUIDE.md` — tabela de estados, nota sobre URL absoluta para crawlers  
- `apps/web/src/pages/ImportPage.tsx`, `ExportPage.tsx`, `AnalysisPage.tsx`, `DiffPage.tsx` — copy PT-BR

## Rationale técnico

- **PNG em `public/`:** formato universal para OG; Vite copia para `dist/` sem pipeline extra.
- **URLs relativas em meta:** adequadas ao deploy na raiz; em subpath, o projeto pode documentar base URL ou `og:url` futuro.
- **E2E:** mesma estratégia do smoke (`page.route`), evitando dependência do backend; asserções usam `first()` onde o JSON duplica texto na UI.

## Assets criados

- `og-image.png` — visual técnico premium (título + subtítulo, paleta coerente com o tema da app).

## Testes adicionados

- `e2e/release.spec.ts`: 3 cenários (tema, export, diff).  
- Comando: `npm run e2e:complement`.

## Riscos residuais

- Plataformas sociais podem fazer cache agressivo da OG image — invalidar após alterações.
- `og:image` relativo: alguns validadores pedem URL absoluta no ambiente de produção.
- O ficheiro `og-image.png` tem tamanho elevado (~900 KB); para repositório ou CDN, considerar compressão (ex. otimização PNG) sem alterar dimensões 1200×630.

## Decisão final

**READY** — Build, smoke e complementar OK; showcase e metadados prontos para repositório e demo, com ressalvas menores de hosting/OG absoluto.
