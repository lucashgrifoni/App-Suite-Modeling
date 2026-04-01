# Handoff — modernização visual otm-web

**Data:** 2026-04-01  
**Decisão de prontidão:** **READY** (com ressalvas menores abaixo)

## Resumo executivo

O frontend `apps/web` foi evoluído para um **dark-first premium** alinhado à paleta verde institucional, com **tokens CSS**, **Tailwind extend**, **shell** (header/navegação/fundo), **componentes base** refinados, **patterns** reutilizáveis (PageHeader, Stepper, StatCard, EmptyState, etc.) e **páginas** atualizadas sem alterar rotas nem contratos da API. O smoke E2E Playwright foi mantido e passou após correção de duplicidade de rótulo de botão na Home.

## Decisões visuais principais

- **Dark como padrão:** `data-theme="dark"` em `index.html`; tema claro preparado em `[data-theme="light"]`.
- **Tipografia:** Outfit (`font-display`) para títulos; DM Sans para corpo.
- **Primário:** gradiente `from-otm-primary to-otm-accent` em CTAs; estados de superfície com bordas translúcidas e sombras em camadas.
- **Motion:** animação de entrada de rota (`animate-page-enter`), lift/tilt utilitário, respeito global a `prefers-reduced-motion`.
- **Sem Framer Motion:** simplicidade e bundle enxuto.

## Novos ficheiros

| Ficheiro | Função |
|----------|--------|
| `apps/web/src/design-system/tokens.ts` | Referência TS de marca/motion/z-index |
| `apps/web/src/hooks/usePrefersReducedMotion.ts` | Hook para preferência de movimento |
| `apps/web/src/components/motion/FadeIn.tsx` | Wrapper de entrada suave |
| `apps/web/src/components/patterns/PageHeader.tsx` | Cabeçalho de página consistente |
| `apps/web/src/components/patterns/SectionHeader.tsx` | Secções internas |
| `apps/web/src/components/patterns/StatCard.tsx` | KPI / métricas |
| `apps/web/src/components/patterns/EmptyState.tsx` | Estados vazios |
| `apps/web/src/components/patterns/Skeleton.tsx` | Loading placeholder |
| `apps/web/src/components/patterns/Stepper.tsx` | Passos do assistente |
| `apps/web/src/components/patterns/Panel.tsx` | Painel simples |
| `apps/web/src/components/patterns/Surface.tsx` | Superfície variante |
| `apps/web/src/components/patterns/GlowDivider.tsx` | Separador com glow |
| `apps/web/src/components/patterns/FileDropZone.tsx` | Zona de arrastar largar (Import) |
| `apps/web/src/components/ui/MethodologyBadge.tsx` | Badge compacta de metodologia |
| `apps/web/src/components/ui/FrameworkTag.tsx` | Tag de catálogo |
| `apps/web/src/components/ui/StatusPill.tsx` | Pill de estado |
| `docs/FRONTEND_MODERNIZATION_PLAN.md` | Diagnóstico e plano (Fase 1) |
| `docs/DESIGN_SYSTEM_FOUNDATION.md` | Documentação de fundações |
| `docs/FRONTEND_MODERNIZATION_VALIDATION.md` | Evidências de validação |
| `docs/FRONTEND_MODERNIZATION_HANDOFF.md` | Este documento |

## Ficheiros alterados (principais)

- `apps/web/src/index.css` — tokens, gradientes, utilitários glass/lift/tilt
- `apps/web/tailwind.config.js` — cores `otm`, sombras, animações, keyframes
- `apps/web/index.html` — `data-theme="dark"`, fonte Outfit
- `apps/web/src/components/layout/AppLayout.tsx` — shell premium, `FadeIn` + `Outlet`
- `apps/web/src/components/ui/*` — Button, Card, Input, Select, Badge, Alert, Checkbox, Label
- `apps/web/src/pages/*` — todas as páginas listadas no pedido

## Removidos

- `apps/web/src/utils/wizardStepPill.ts` — substituído por `Stepper` (ficou sem referências)

## Dependências

- **Nenhuma dependência npm nova** (continuação em React 18 + Vite 5 + Tailwind + Playwright).

## Riscos residuais

- **Contraste** em monitores com brilho baixo: rever tons `text-otm-text-muted` vs fundo em hardware real.
- **Tema claro:** tokens definidos; UI não expõe ainda toggle de tema (evolução futura).
- **Bundle:** ~228 kB JS gzip ~70 kB após build — aceitável; `React.lazy` por rota pode ser próximo passo opcional.

## Recomendações futuras

- Toggle `data-theme` com persistência em `localStorage`
- Storybook ou página interna de documentação de componentes
- Testes E2E adicionais para Import (drop) e Diff (JSON inválido)

## Checklist de regressão

- [x] Rotas inalteradas
- [x] IDs críticos preservados (`#methodology`, etc.)
- [x] Textos do smoke preservados (com excepção do botão duplicado renomeado na grelha)
- [x] `npm run ci:build` em `apps/web`
- [x] `npm run e2e:smoke`

## Decisão final

**READY** — critérios de aceitação do pedido cumpridos com implementação real, documentação e validação automatizada.
