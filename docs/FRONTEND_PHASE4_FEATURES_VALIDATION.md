# Validação — Fase 4 (diagrama, PDF, histórico) — otm-web

**Data:** 2026-04-01 (revalidação escopo Fase 4)

## Comandos

| Comando | Resultado |
|---------|-----------|
| `npm run ci:build` (`apps/web`) | OK (última execução) |
| `npm run e2e:smoke` | OK (1 teste) |
| `npm run e2e:phase4` (`diagram` + `pdf` + `history`) | OK (3 testes) |

## Funcional (resumo)

| Área | Verificação |
|------|-------------|
| Diagrama `/review` | React Flow; **editar por omissão** (DnD); alternar «Visualizar»; posições em `sessionStorage`; modelo em sessão |
| PDF | `generateReportPdf` com import dinâmico de `jspdf`; botão em Export |
| Histórico `/history` | `localStorage` `otm.analysis.history`, máx. 20 entradas; métricas + resumo JSON; restore e export/PDF por entrada |
| API | Sem alteração de endpoints; export API inalterado |

## Testes E2E

- `e2e/diagram.spec.ts` — canvas e toolbar de edição
- `e2e/pdf.spec.ts` — descarga `.pdf`
- `e2e/history.spec.ts` — lista após análise
- `e2e/_phase4Mocks.ts` — mocks partilhados

## Critérios de aceite

Diagrama editável, PDF funcional, histórico com restore/export parcial, rotas preservadas, build e E2E OK.
