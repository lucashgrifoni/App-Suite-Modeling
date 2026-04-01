# Handoff — refinamento fase 2 (otm-web)

**Data:** 2026-04-01  
**Decisão:** **READY**

## Resumo executivo

Segunda fase do frontend: **lazy-loading** por rota com `Suspense` e fallback alinhado ao DS, **sistema de toast** global leve (sem dependências novas), **ThemeProvider** com toggle Escuro/Claro/Sistema e persistência, **refatoração da `AnalysisPage`** em componentes em `components/analysis/`, **toasts e estados** reforçados nas páginas com acções assíncronas, **anti-FOUC** de tema via script inline, e **ajustes de layout** (`min-w-0` no `main`). Build e smoke E2E mantêm-se verdes.

## Ficheiros criados

| Ficheiro | Descrição |
|----------|-----------|
| `docs/FRONTEND_REFINEMENT_PHASE2_PLAN.md` | Plano e critérios da fase |
| `docs/FRONTEND_REFINEMENT_PHASE2_VALIDATION.md` | Evidências de validação |
| `docs/FRONTEND_REFINEMENT_PHASE2_HANDOFF.md` | Este documento |
| `apps/web/src/context/ThemeContext.tsx` | Preferência de tema + efeito DOM |
| `apps/web/src/context/ToastContext.tsx` | API `useToast()` + viewport |
| `apps/web/src/components/layout/RouteFallback.tsx` | Fallback do `Suspense` |
| `apps/web/src/components/layout/ThemeToggle.tsx` | Select de tema |
| `apps/web/src/components/analysis/RunEngineCard.tsx` | Painel executar motor |
| `apps/web/src/components/analysis/AnalysisMetricsGrid.tsx` | Grelha de métricas |
| `apps/web/src/components/analysis/Plot4aiContextCard.tsx` | Secção PLOT4ai |
| `apps/web/src/components/analysis/ExplanationsSection.tsx` | Explicabilidade |
| `apps/web/src/components/analysis/RemediationBacklogCard.tsx` | Backlog |
| `apps/web/src/components/analysis/MethodologyInsightsSection.tsx` | Insights |
| `apps/web/src/components/analysis/ThreatsAnalysisCard.tsx` | Lista de ameaças + export |

## Ficheiros alterados (principais)

- `apps/web/src/context/SessionContext.tsx` — persistência **síncrona** em `setDocument` / `setAnalysis` (corrige corrida com reload/navegação imediata; E2E estável)
- `apps/web/src/App.tsx` — `React.lazy` por página + `Suspense`
- `apps/web/src/main.tsx` — `ThemeProvider`, `ToastProvider`
- `apps/web/index.html` — script de tema inicial; removido `data-theme` estático do `<html>`
- `apps/web/src/components/layout/AppLayout.tsx` — `ThemeToggle`, `main` refinado
- `apps/web/src/pages/AnalysisPage.tsx` — orquestração fina + toasts
- `apps/web/src/pages/HomePage.tsx`, `ImportPage.tsx`, `ExportPage.tsx`, `DiffPage.tsx`, `ReviewPage.tsx`, `WizardPage.tsx`, `TemplatesPage.tsx` — integração `useToast` onde aplicável

## Rationale técnico por bloco

| Bloco | Decisão |
|-------|---------|
| Lazy + Suspense | Reduz JS inicial; fallback com `Skeleton` evita “salto” vazio |
| Toast em Context | Sem lib externa; pilha máx. 5; `aria-live` para leitores |
| Tema | Reutiliza tokens `[data-theme]` existentes; script inline alinha primeiro paint com `localStorage` |
| Analysis | Subcomponentes reduzem densidade visual e complexidade do ficheiro página |
| `memo` em linha de ameaça | Lista potencialmente longa; re-render mais barato |

## Dependências

- **Nenhuma** nova em `package.json`.

## Riscos residuais

- Toasts **não** empilham gestão de foco com diálogos futuros (avaliar `inert` no resto da página se necessário).
- Tema **sistema** depende de `matchMedia` (comportamento esperado em browsers modernos).

## Oportunidades futuras

- Testes E2E para toggle de tema e aparição de toast.
- `React.memo` adicional em cartões de lista se perfilar re-renders.
- Portal dedicado para toasts se surgirem modais com z-index conflituoso.

## Decisão final

**READY** — critérios da fase 2 cumpridos: performance de navegação melhorada, feedback global, Analysis mais legível, tema funcional, validação automatizada OK.
