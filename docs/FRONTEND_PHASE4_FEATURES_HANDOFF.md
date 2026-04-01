# Handoff — Fase 4 (diagrama, PDF, histórico) — otm-web

## Resumo executivo

Três funcionalidades de produto no frontend: **editor de diagrama** (React Flow, **modo edição por omissão** para drag-and-drop imediato, alternância «Visualizar»), **relatório PDF** na página Exportar (`jspdf`, descarga no browser) e **histórico** (`/history`, ao lado de Exportar na navegação) com snapshots após análise/export, **visualização** (métricas + resumo JSON expansível), **restaurar** e **export/PDF** por entrada. A API REST **não** foi alterada nesta fase.

## Ficheiros criados

- `docs/FRONTEND_PHASE4_FEATURES_PLAN.md`
- `docs/FRONTEND_PHASE4_FEATURES_VALIDATION.md`
- `docs/FRONTEND_PHASE4_FEATURES_HANDOFF.md` (este)
- `apps/web/src/utils/diagramSanitize.ts`
- `apps/web/src/utils/diagramLayoutStorage.ts`
- `apps/web/src/utils/analysisHistoryStorage.ts`
- `apps/web/src/types/analysisHistory.ts`
- `apps/web/src/context/AnalysisHistoryContext.tsx`
- `apps/web/src/lib/generateReportPdf.ts`
- `apps/web/src/components/diagram/ComponentNode.tsx`
- `apps/web/src/components/diagram/ThreatModelDiagram.tsx`
- `apps/web/src/pages/HistoryPage.tsx`
- `apps/web/e2e/_phase4Mocks.ts`, `e2e/diagram.spec.ts`, `e2e/pdf.spec.ts`, `e2e/history.spec.ts`

## Ficheiros alterados

- `apps/web/package.json` — dependência `jspdf`; script `e2e:phase4`
- `apps/web/src/App.tsx` — `AnalysisHistoryProvider`, rota `/history`
- `apps/web/src/components/layout/AppLayout.tsx` — link Histórico
- `apps/web/src/pages/ReviewPage.tsx` — diagrama interativo
- `apps/web/src/pages/ExportPage.tsx` — PDF + `appendSnapshot` após export
- `apps/web/src/pages/AnalysisPage.tsx` — `appendSnapshot` após análise

## Decisões técnicas

| Tema | Decisão |
|------|---------|
| Posições no diagrama | `sessionStorage` (`otm.web.diagramLayout`); não enviar coordenadas ao backend |
| PDF | Apenas texto; sem HTML embutido; `import()` dinâmico de `jspdf` |
| Histórico | `localStorage` (`otm.analysis.history`), máximo 20 entradas; cópia profunda via JSON |
| Segurança | `sanitizeDiagramLabel` remove tags; rótulos tratados como texto |

## Testes

- `npm run e2e:smoke` — regressão fluxo mínimo
- `npm run e2e:phase4` — diagrama, PDF, histórico

## Riscos residuais

- `jspdf` continua um chunk grande quando o PDF é gerado (carregamento sob demanda).
- Histórico não sincroniza entre separadores/dispositivos; quota `localStorage` pode falhar em modo privado.
- React Flow não valida o modelo no cliente — continua a depender da validação no servidor.

## Próximos passos sugeridos

- Teste E2E de “Restaurar” no histórico (fluxo com confirmação).
- Sincronização opcional do histórico com backend em versões futuras.
- Compressão ou pruning mais agressivo do histórico se o tamanho crescer.

## Alterações recentes (rodada de alinhamento ao escopo)

- Diagrama: `editMode` inicial `true` em `ThreatModelDiagram.tsx`; copy em `ReviewPage.tsx`; E2E `diagram.spec.ts` ajustado.
- Histórico: métricas por snapshot + `<details>` com JSON de resumo em `HistoryPage.tsx`.
- Documentação: `FRONTEND_PHASE4_FEATURES_*.md` actualizados.

## Decisão

**READY** — diagrama editável por omissão, PDF na aba Exportar, histórico com visualização e restore; build e E2E (smoke + phase4) verdes na última execução local.
