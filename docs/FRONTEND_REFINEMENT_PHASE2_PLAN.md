# Plano — refinamento técnico fase 2 (otm-web)

**Data:** 2026-04-01  
**Base:** estado pós-`FRONTEND_MODERNIZATION_*` (READY)

## 1. Diagnóstico pós-modernização

O frontend está **coerente visualmente**, com tokens, shell, patterns e build/E2E estáveis. A arquitetura permanece simples (rotas planas, um contexto de sessão), adequada a OSS.

## 2. Pontos fortes já resolvidos

- Identidade dark premium e paleta institucional
- Componentes base e patterns reutilizáveis
- Motion leve com `prefers-reduced-motion`
- Documentação de fundações e handoff da fase 1
- Smoke E2E cobrindo fluxo crítico

## 3. Gaps ainda abertos

| Gap | Impacto |
|-----|---------|
| Bundle único carrega todas as páginas | TTI em rotas raras (Analysis, Diff) |
| Sem feedback global (toast) | Ações assíncronas dependem só de Alert inline |
| Tema claro só em CSS, sem UI | Utilizadores não escolhem tema |
| `AnalysisPage` monolítica | Manutenção e Sonar (complexidade) |
| Estados de sucesso pouco celebrados | UX de “conclusão” fraca em Export/Import |

## 4. Riscos de regressão

- **Lazy routes:** Suspense mal posicionado pode esconder conteúdo ou duplicar fallback
- **Tema:** FOUC se não houver script inline mínimo antes do paint
- **E2E:** Rotas e textos canónicos (`#methodology`, botões) devem permanecer
- **Toast:** z-index e focus não devem roubar teclado de modais futuros

## 5. Backlog priorizado (fase 2)

1. **P0** — `React.lazy` + `Suspense` + fallback DS
2. **P0** — Toast global (contexto leve, sem lib pesada)
3. **P1** — Theme toggle + persistência + sistema
4. **P1** — Estados async/empty/success refinados nas páginas indicadas
5. **P1** — Refatorar `AnalysisPage` em subcomponentes
6. **P2** — Passada a11y/responsividade documentada
7. **P2** — Validação + handoff fase 2

## 6. Ficheiros previstos (criar / alterar)

**Criar**

- `docs/FRONTEND_REFINEMENT_PHASE2_PLAN.md` (este)
- `docs/FRONTEND_REFINEMENT_PHASE2_VALIDATION.md`
- `docs/FRONTEND_REFINEMENT_PHASE2_HANDOFF.md`
- `apps/web/src/context/ThemeContext.tsx`
- `apps/web/src/context/ToastContext.tsx`
- `apps/web/src/components/layout/RouteFallback.tsx`
- `apps/web/src/components/layout/ThemeToggle.tsx`
- `apps/web/src/components/feedback/ToastViewport.tsx` (ou integrado no context)
- `apps/web/src/components/analysis/*.tsx` (submódulos da análise)

**Alterar**

- `apps/web/index.html` — script anti-FOUC de tema (opcional mínimo)
- `apps/web/src/main.tsx` — providers
- `apps/web/src/App.tsx` — lazy + Suspense
- `apps/web/src/components/layout/AppLayout.tsx` — toggle + viewport de toasts
- `apps/web/src/pages/AnalysisPage.tsx` — composição fina
- `apps/web/src/pages/*` — toasts / loading onde aplicável

## 7. Critérios de aceite objetivos

1. Navegação entre rotas principais usa code-splitting sem erros de consola
2. `useToast()` disponível com variantes success/error/warning/info
3. Tema escolhível (dark/light/sistema) com persistência e fallback seguro
4. `AnalysisPage` dividida em componentes com comportamento preservado
5. `npm run ci:build` e `npm run e2e:smoke` verdes
6. Sem alteração de contratos API nem paths de rota
