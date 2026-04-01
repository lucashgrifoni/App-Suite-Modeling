# Handoff — Fase 3 (product polish) — otm-web

## Resumo executivo

A UI foi reforçada como **ferramenta técnica premium**: Home com narrativa de valor e pipeline explícito, componentes de onboarding reutilizáveis (`WorkflowGuide`, `QuickStartPanel`, `HelpCallout`, `ContextHint`), leitura analítica com **barra L×I** (CSS) em métricas e ameaças, Diff com cartões mais escaneáveis e destaque de risco quando a análise está incluída, **ErrorBoundary** no layout, **favicon SVG** e metadados em `index.html`, mais guia de screenshots.

## Ficheiros criados

- `apps/web/public/favicon.svg`
- `apps/web/src/components/analytics/RiskScoreBar.tsx` (evoluído com variantes `default` / `compact` / `none`)
- `apps/web/src/components/onboarding/WorkflowGuide.tsx`
- `apps/web/src/components/onboarding/HelpCallout.tsx`
- `apps/web/src/components/onboarding/ContextHint.tsx`
- `apps/web/src/components/onboarding/QuickStartPanel.tsx`
- `apps/web/src/components/error/ErrorBoundary.tsx`
- `docs/SCREENSHOT_GUIDE.md`
- `docs/FRONTEND_PHASE3_PRODUCT_POLISH_VALIDATION.md`
- `docs/FRONTEND_PHASE3_PRODUCT_POLISH_HANDOFF.md` (este ficheiro)

## Ficheiros alterados (principais)

- `apps/web/index.html` — description, theme-color, og/twitter mínimos, favicon
- `apps/web/src/pages/HomePage.tsx` — hero, quick start, pipeline, callouts
- `apps/web/src/pages/ImportPage.tsx`, `WizardPage.tsx`, `ExportPage.tsx`, `AnalysisPage.tsx`, `DiffPage.tsx` — onboarding contextual
- `apps/web/src/components/layout/AppLayout.tsx` — `ErrorBoundary` no `Outlet`
- `apps/web/src/components/analysis/AnalysisMetricsGrid.tsx`, `ThreatsAnalysisCard.tsx`
- `apps/web/src/components/patterns/StatCard.tsx` — prop `footer` (já existente; uso em métricas)
- `apps/web/src/pages/DiffPage.tsx` — `DiffSummaryCard`, `DiffRiskDeltaCard`, `AggregateBlock` refinado

## Rationale técnico (por bloco)

| Bloco | Decisão |
|-------|---------|
| Barras de risco | Só CSS + ARIA; sem chart library — baixo custo de bundle |
| Onboarding | Componentes pequenos e compostos; conteúdo em PT-PT alinhado ao produto |
| ErrorBoundary | Classe React clássica; fallback com ações “Recarregar” / início — sem router dependency extra |
| Meta / favicon | SVG leve; OG básico para repositório e demos estáticos |
| Diff | Subcomponentes extraídos para legibilidade e limite de complexidade cognitiva |

## Impactos visuais e de UX

- Primeira impressão na Home mais **memorável** sem virar landing de marketing agressivo.
- Utilizador vê **onde está no pipeline** em quase todas as etapas principais.
- Análise e Diff **mais legíveis** para demo e screenshot.

## Riscos residuais

- ErrorBoundary não captura erros em event handlers nem em código assíncrono fora de render.
- Metadados OG não incluem imagem dedicada (`og:image`) — pode ser adicionada numa fase futura.

## Oportunidades futuras

- `og:image` estática no `public/` para Social Preview.
- Testes E2E adicionais para Diff com fixture mock (se API mockável).
- `FirstRunEmptyState` dedicado se o fluxo de sessão evoluir.

## Decisão final

**READY** — Build e smoke E2E OK; objetivos da fase 3 cumpridos com riscos conhecidos e aceitáveis para OSS/demo.
