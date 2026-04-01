# Validação — refinamento fase 2 (otm-web)

**Data:** 2026-04-01

## Comandos automatizados

| Comando | Resultado |
|---------|-----------|
| `npm run ci:build` (`apps/web`) | OK |
| `npm run e2e:smoke` (Playwright Chromium) | OK |

## Code splitting

- Build de produção gera chunks por rota (ex.: `AnalysisPage-*.js`, `WizardPage-*.js`, `HomePage-*.js`).
- Chunk principal `index-*.js` ~179 kB gz ~59 kB (antes ~228 kB / ~70 kB monolítico).

## Tema

- **Script inline** em `index.html` aplica `data-theme` antes do paint para evitar FOUC.
- **Toggle** no header: Escuro / Claro / Sistema; persistência `localStorage` chave `otm.web.themePreference`.
- Verificação manual: alternar tema e confirmar contraste legível em ambos.

## Toasts

- Provider em `main.tsx`; viewport fixo canto inferior direito, `aria-live="polite"`, fecho manual.
- Disparo em fluxos: Home (criar modelo), Import, Export, Diff, Review, Wizard (erro validação), Templates, Analysis (motor/backlog/recomendação).

## Estados assíncronos

- Import: `aria-busy` no formulário durante pedido.
- Export: toast de aviso se nenhum formato seleccionado.
- Analysis: `EmptyState` quando não há resultado; subcomponentes para leitura.

## Responsividade / a11y (revisão aplicada)

- `main` com `min-w-0` e altura mínima para evitar overflow horizontal comum em flex.
- Theme toggle com `<label>` + `sr-only` e `select` nativo (teclado e leitores).
- Toasts com botão fechar rotulado.

## Rotas lazy

- Navegação entre `/`, `/wizard`, `/analysis`, `/export` carrega chunks distintos (confirmado pelo relatório de build e ausência de erros no smoke).

## Sessão (regressão corrigida)

- `SessionContext` passou a **persistir `sessionStorage` de forma síncrona** em `setDocument` / `setAnalysis` (removidos `useEffect` duplicados). Isto evita corrida em testes E2E e reloads rápidos onde o documento ainda não tinha sido escrito antes de `page.goto("/analysis")`.

**Estado:** critérios de aceite da fase 2 cumpridos no âmbito automatizado e checklist manual acima.
