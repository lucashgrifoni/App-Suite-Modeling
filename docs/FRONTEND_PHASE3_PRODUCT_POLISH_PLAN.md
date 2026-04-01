# Plano — fase 3: product polish & showcase (otm-web)

**Data:** 2026-04-01  
**Base:** fases 1–2 concluídas (DS, lazy routes, toast, tema, Analysis refactor, E2E verde).

## 1. Diagnóstico atual

O frontend está **técnicamente sólido**: tokens, shell, patterns, code-splitting, feedback global e sessão persistente de forma síncrona. Falta, sobretudo, **narrativa de produto** na entrada (Home), **orientação explícita do fluxo** entre ecrãs e **camada visual analítica** mais demonstrável em Analysis/Diff para screenshots e README.

## 2. Pontos fortes consolidados

- Identidade dark premium e paleta consistente
- Rotas lazy e bundle modular
- Toasts e tema acessíveis na base
- Analysis modularizada em `components/analysis/`

## 3. Gaps (UX / showcase / OSS)

| Gap | Impacto |
|-----|---------|
| Home ainda “dashboard técnico” sem storytelling suficiente | Primeira impressão em GitHub/demo |
| Fluxo import→…→diff pouco explícito fora da Home | Curva de adoção |
| Métricas de risco sem visualização imediata | Demo analítica |
| Sem ErrorBoundary | Erros de render pouco amigáveis |
| Meta/favicon genéricos | SEO e abas do browser |
| Falta guia de screenshots | Marketing OSS manual |

## 4. Oportunidades de alto impacto / baixo risco

- Componentes **WorkflowGuide**, **HelpCallout**, **QuickStartPanel** reutilizáveis
- **Barras de risco** CSS-only (sem libs de charts)
- **ErrorBoundary** único à volta do `Outlet`
- **favicon.svg + meta** sem dependências

## 5. Riscos de regressão

- E2E depende de `h1` “Threat modeling, passo a passo” e botão “Criar novo modelo” — preservar
- Não alterar IDs (`#methodology`, etc.)
- Evitar aumento de JS desnecessário

## 6. Backlog priorizado

1. Home premium (hero + fluxo + prova de valor)
2. Patterns de onboarding (guia, hints, callouts)
3. Analysis/Diff: barras e hierarquia analítica
4. ErrorBoundary + fallback
5. Meta, favicon, SCREENSHOT_GUIDE
6. Validação + handoff

## 7. Ficheiros previstos

- `docs/FRONTEND_PHASE3_PRODUCT_POLISH_PLAN.md` (este)
- `docs/FRONTEND_PHASE3_PRODUCT_POLISH_VALIDATION.md`
- `docs/FRONTEND_PHASE3_PRODUCT_POLISH_HANDOFF.md`
- `docs/SCREENSHOT_GUIDE.md`
- `apps/web/public/favicon.svg`
- `apps/web/src/components/onboarding/*` (WorkflowGuide, QuickStartPanel, ContextHint, HelpCallout)
- `apps/web/src/components/analytics/RiskScoreBar.tsx`, `RiskScoreCard.tsx`
- `apps/web/src/components/error/ErrorBoundary.tsx`
- Alterações: `HomePage.tsx`, `AppLayout.tsx`, `AnalysisMetricsGrid.tsx`, `ThreatsAnalysisCard.tsx`, `DiffPage.tsx`, `index.html`, páginas com hints leves

## 8. Critérios de aceite

1. Home mais clara em valor e fluxo, sem virar landing de marketing vazio
2. Utilizador percebe o pipeline técnico em ≤1 scroll na Home
3. Analysis mostra leitura de risco mais imediata (barras/métricas)
4. Diff/Export com hierarquia visual melhor para demo
5. ErrorBoundary com fallback alinhado ao DS
6. Meta + favicon coerentes com branding
7. `npm run ci:build` e `npm run e2e:smoke` verdes
