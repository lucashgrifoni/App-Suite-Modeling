# Plano — Release assets, showcase final e QA complementar (otm-web)

## Objetivo

Fechar o frontend para **publicação e showcase** com impacto controlado: OG image estática, guia de screenshots reforçado, testes E2E complementares estáveis, revisão curta de copy e documentação de validação/handoff — **sem redesign** e **sem regressões** de build ou smoke.

## Escopo exato

| Área | Entrega |
|------|---------|
| Social preview | `public/og-image.png` (1200×630), metadados `og:image` / `twitter` em `index.html` |
| Showcase | Atualizar `docs/SCREENSHOT_GUIDE.md` (estados ideais por ecrã) |
| QA E2E | `e2e/release.spec.ts`: tema (data-theme), export (UI com sessão), diff (compare mockado) |
| Copy | Ajustes PT-BR (ex.: atual vs actual, selecionado) onde houver ganho claro |
| Docs | `FRONTEND_FINAL_RELEASE_ASSETS_VALIDATION.md`, `FRONTEND_FINAL_RELEASE_ASSETS_HANDOFF.md` |

## Ficheiros previstos

- `apps/web/public/og-image.png` (novo)
- `apps/web/index.html` (meta og:image, twitter:card summary_large_image)
- `apps/web/e2e/release.spec.ts` (novo)
- `apps/web/package.json` (script `e2e:complement` opcional)
- `docs/SCREENSHOT_GUIDE.md` (atualizado)
- `docs/FRONTEND_FINAL_RELEASE_ASSETS_*.md` (novos)

## Riscos mínimos

- OG em PNG grande (~100–300 KB): aceitável para rede; sem runtime impact.
- E2E extra: mocks alinhados a `**/api/v1/...` — frágil se paths mudarem (mitigado: mesma convenção do smoke).

## Critérios de aceite

1. `og:image` servida em `/og-image.png` e referenciada nos meta tags.
2. Guia de screenshots com estados recomendados por tela.
3. Pelo menos um ficheiro E2E complementar com cenários úteis e estáveis.
4. Copy mais consistente (PT-BR) nos pontos acordados.
5. `npm run ci:build` OK; `npm run e2e:smoke` OK; `e2e:complement` OK.
6. Sem alteração de contratos API nem rotas.
