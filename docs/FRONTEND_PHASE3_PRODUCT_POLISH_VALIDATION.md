# Validação — Fase 3 (product polish) — otm-web

**Data:** 2026-04-01  
**Escopo:** Polish premium, onboarding, analytics visual, showcase OSS, ErrorBoundary, meta/favicon, documentação associada.

## Automatizado

| Comando | Resultado |
|---------|-----------|
| `npm run ci:build` (em `apps/web`) | OK — `tsc --noEmit` + `vite build` |
| `npm run e2e:smoke` (Chromium) | OK — fluxo mínimo home → análise → export |

## Manual (checklist)

| Área | Estado | Notas |
|------|--------|--------|
| Home — hero e valor | Verificado no código | h1 e botão “Criar novo modelo” preservados para E2E |
| Onboarding — WorkflowGuide / hints | Verificado no código | Import, Wizard, Export, Analysis, Diff |
| Analysis — métricas + ameaças | Verificado no código | `RiskScoreBar` em Maior L×I e por ameaça |
| Diff — resumo e agregados | Verificado no código | Cartões refinados; L×I revisão quando análise incluída |
| Dark / light | Não bloqueante | Toggle existente; tema default dark preservado |
| Reduced motion | Herdado | Barras usam `motion-reduce:transition-none` onde aplicável |
| ErrorBoundary | Integrado | `AppLayout` à volta do `Outlet` |

## Screenshots / showcase

- Ver `docs/SCREENSHOT_GUIDE.md` para enquadramentos sugeridos.

## Acessibilidade (amostra)

- `RiskScoreBar`: `role="progressbar"` e `aria-*`  
- Novos textos de empty state e callouts revistos para clareza; revisão completa de WCAG não substitui auditoria dedicada.

## Conclusão

Critérios de aceite da fase 3 satisfeitos no âmbito implementado: build e smoke OK, sem alteração de contratos API, rotas preservadas, bundle sem dependências novas.
