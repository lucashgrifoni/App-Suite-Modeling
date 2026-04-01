# Validação da modernização do frontend (otm-web)

**Data:** 2026-04-01

## Comandos executados

| Comando | Resultado |
|---------|-----------|
| `npm run typecheck` (em `apps/web`) | OK |
| `npm run build` (Vite produção) | OK |
| `npm run e2e:smoke` (Playwright Chromium) | OK |

## Smoke E2E

- Ficheiro: `apps/web/e2e/smoke.spec.ts`
- Cenário: home → criar modelo → análise (mock API) → export → descarregar
- Ajuste aplicado: dois botões com o mesmo nome “Criar novo modelo” na Home causavam *strict mode violation*; o CTA duplicado na grelha foi renomeado para “Iniciar modelo em branco” mantendo o texto canónico no hero.

## Verificação manual recomendada (checklist)

- [ ] Rotas `/`, `/templates`, `/import`, `/wizard`, `/review`, `/analysis`, `/export`, `/diff` carregam sem erros de consola
- [ ] Contraste legível em dark (texto principal vs superfícies)
- [ ] `prefers-reduced-motion`: animações de página/card reduzidas (definido em `index.css`)
- [ ] Foco visível em links, botões e inputs
- [ ] Estados vazios: templates sem dados (servidor), análise sem resultado
- [ ] Responsividade: header e grelhas em viewport estreita

## Acessibilidade (básica)

- Landmarks: `main` implícito no layout; stepper com `nav` + `aria-label`
- Alerts com `role="alert"`
- Labels associados a inputs (`htmlFor` / `id`)
- `sr-only` no input de ficheiro dentro da zona de drop (Import)

## Performance

- Sem biblioteca de animação extra; motion via CSS + Tailwind `keyframes`
- Efeitos 3D limitados a classes utilitárias (`.otm-card-lift`, `.otm-tilt-hover`) com override em `prefers-reduced-motion`

## Segurança frontend

- Sem `dangerouslySetInnerHTML` novo
- Conteúdo dinâmico continua como texto/React children
- Download de artefactos via `Blob` + object URL (padrão existente)

**Status:** validação automatizada principal concluída com sucesso.
