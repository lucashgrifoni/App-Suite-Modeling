# Fundação do design system — otm-web

## Princípios

- **Dark-first:** `data-theme="dark"` no `<html>` (default). `data-theme="light"` preparado para evolução.
- **Paleta oficial:** `#6AE899`, `#56FF95`, `#7DFABE`, `#76DB9B`, `#30B27F` mapeadas para tokens semânticos (`--otm-primary`, `--otm-accent`, etc.).
- **Neutros:** escalas `--otm-green-*` para superfícies em dark; texto `--otm-text` / `--otm-text-muted`.
- **Sem drift:** preferir `bg-otm-surface-*`, `text-otm-text`, `border-otm-border` no Tailwind; variáveis CSS em `src/index.css`.

## Camadas

1. **Tokens CSS** — `index.css` (`:root` / `[data-theme="dark"]`).
2. **Tokens TS** — `src/design-system/tokens.ts` (referência e uso programático).
3. **Tailwind** — `tailwind.config.js` mapeia cores/sombras/radius/animation para utilitários `otm-*`.
4. **Primitives** — `components/ui/*` (Button, Card, Input, …).
5. **Patterns** — `components/patterns/*` (PageHeader, EmptyState, Stepper, …).
6. **Páginas** — compõem patterns + primitives; sem lógica de API nas primitives.

## Tokens principais

| Categoria | Exemplo | Uso |
|-----------|---------|-----|
| Cor primária | `--otm-primary` (#30B27F) | CTAs, links fortes, focus |
| Accent | `--otm-accent` (#56FF95) | highlights, glows sutis |
| Superfície | `--otm-surface-1` … `3` | cards, painéis |
| Texto | `--otm-text`, `--otm-text-muted` | corpo e meta |
| Borda | `--otm-border`, `--otm-border-strong` | separação hierárquica |
| Estados | `--otm-success`, `--otm-warning`, `--otm-danger`, `--otm-info` | feedback (não só cor — ícones/texto) |
| Focus | `--otm-ring` | `:focus-visible` e `ring-otm` |
| Sombras | `--otm-shadow-md`, `--otm-shadow-glow` | profundidade |
| Blur | `--otm-blur-glass` | glassmorphism |
| Motion | `transition-duration-otm`, `ease-otm` | microinterações |

## Tipografia

- **Corpo / UI:** DM Sans (`font-sans`).
- **Títulos / marketing:** Outfit (`font-display`) em PageHeader e hero.

## Acessibilidade

- Contraste verificado para texto principal sobre `surface-2` em dark.
- `prefers-reduced-motion`: animações reduzidas em `index.css` + utilitários condicionais.
- Foco visível global em `:focus-visible`.

## Extensão futura

- Toggle de tema: alterar `data-theme` em `<html>`; tokens light já definidos em `[data-theme="light"]`.
