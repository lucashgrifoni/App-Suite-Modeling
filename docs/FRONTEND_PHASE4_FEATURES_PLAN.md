# Plano — Fase 4: diagrama editável, PDF e histórico (otm-web)

## Objetivo

Adicionar três capacidades de produto no frontend existente, **sem alterar contratos da API REST** nem quebrar o fluxo wizard → diagrama → análise → export/diff.

## Impacto das features

| Feature | Impacto | Notas |
|--------|---------|--------|
| Diagrama editável | Alto na UX da página `/review` | React Flow já está no `package.json`; posições persistidas em `sessionStorage` para não enviar campos extra ao backend. |
| PDF | Novo artefacto só no cliente | Geração com `jspdf` (texto estruturado A4); não há `POST` novo. |
| Histórico | Estado local + UX | `localStorage` chave `otm.analysis.history`, máx. 20 entradas; restore sobrescreve sessão com confirmação. |

## Dependências existentes

- **React Flow** (`reactflow`): canvas de diagrama.
- **SessionContext**: `document`, `setDocument`, `analysis`, `setAnalysis`.
- **Export**: `exportArtifacts` para formatos existentes; PDF é caminho separado.

## Estratégia por feature

### 1) Diagrama (drag-and-drop)

- Mapear `components` → nós, `data_flows` → arestas; IDs estáveis (`component.id`, `data_flow.id`).
- **Por omissão: modo Editar** (drag-and-drop, ligações, CRUD). Modo **Visualizar** = só pan/zoom, sem edição estrutural.
- Toolbar: adicionar nó (kind default), remover selecionado, reposicionar layout (grid).
- **Labels**: função `sanitizeDiagramLabel` (remover tags, truncar) antes de gravar no documento.
- **Layout**: `sessionStorage` `otm.web.diagramLayout` — `Record<componentId, {x,y}>` para não alterar o JSON enviado à API.

### 2) PDF

- `jspdf`: secções — título, resumo, métricas (se análise), lista curta de ameaças heurísticas.
- Botão dedicado em Export (não misturar com `ExportFormat` da API).
- `requestAnimationFrame` / `queueMicrotask` para não bloquear a UI de forma perceptível.

### 3) Histórico

- Tipo `AnalysisHistoryEntry`: `id`, `timestamp`, `summaryLine`, `maxScore`, `systemType`, `document`, `analysis`.
- Append após **análise bem-sucedida** e após **exportação bem-sucedida** (snapshot atual).
- Página `/history`: lista, detalhe, Restaurar (confirm), Exportar (reutiliza fluxo PDF/artefactos na sessão após restore).

## Riscos

- **Performance**: React Flow com muitos nós — `memo` nos nós customizados; evitar `setState` global desnecessário.
- **Storage**: quota `localStorage` — limite 20 entradas + compressão futura se necessário.
- **UX**: restore substitui sessão — modal de confirmação.

## Ficheiros previstos (criar / alterar)

- **Criar**: `components/diagram/*`, `utils/diagramSanitize.ts`, `utils/diagramLayoutStorage.ts`, `lib/generateReportPdf.ts`, `context/AnalysisHistoryContext.tsx`, `pages/HistoryPage.tsx`, `components/history/*`, `e2e/history.spec.ts`, `e2e/pdf.spec.ts` (ou `phase4.spec.ts`).
- **Alterar**: `ReviewPage.tsx`, `ExportPage.tsx`, `AnalysisPage.tsx`, `App.tsx`, `AppLayout.tsx`, `main.tsx` (provider), `package.json`.

## Critérios de aceite

1. Diagrama em modo edição permite drag, ligações novas, remoção e labels seguros.
2. PDF descarrega ficheiro válido com conteúdo coerente.
3. Histórico lista, restaura e permite export após restore.
4. Rotas antigas intactas; smoke E2E passa; novos E2E estáveis.

## Scripts npm (`apps/web`)

- `npm run e2e:phase4` — corre `diagram.spec`, `pdf.spec`, `history.spec`.
