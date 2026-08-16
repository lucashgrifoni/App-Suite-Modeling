import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { ComponentNode, type OtmNodeData } from "./ComponentNode";
import { sanitizeDiagramLabel } from "../../utils/diagramSanitize";
import { removeComponents } from "../../utils/documentNormalize";
import {
  clearDiagramLayout,
  loadDiagramLayout,
  saveDiagramLayoutPatch,
} from "../../utils/diagramLayoutStorage";
import { COMPONENT_KINDS, type OtmDataFlow, type OtmDocument } from "../../types/document";

function gridPos(i: number): { x: number; y: number } {
  const col = i % 4;
  const row = Math.floor(i / 4);
  return { x: col * 220 + 24, y: row * 140 + 24 };
}

function buildNodes(doc: OtmDocument, editMode: boolean): Node<OtmNodeData>[] {
  const layout = loadDiagramLayout();
  return doc.components.map((c, i) => ({
    id: c.id,
    type: "otm",
    position: layout[c.id] ?? gridPos(i),
    data: { label: sanitizeDiagramLabel(c.name), kind: c.kind },
    draggable: editMode,
    selectable: true,
    deletable: editMode,
  }));
}

// Module-scoped marker config so each edge reuses the same object reference and
// React Flow's prop-stability heuristic does not flag the diagram on re-render.
const EDGE_MARKER_END = { type: MarkerType.ArrowClosed, color: "var(--otm-mint-400)" } as const;

function buildEdges(doc: OtmDocument, editMode: boolean): Edge[] {
  return doc.data_flows.map((f) => ({
    id: f.id,
    source: f.from_component,
    target: f.to_component,
    label: f.name ? sanitizeDiagramLabel(f.name) : undefined,
    markerEnd: EDGE_MARKER_END,
    deletable: editMode,
  }));
}

// Module-scoped to keep the reference stable across re-renders and React
// StrictMode double-mounts — silences React Flow warning #002.
const nodeTypes = Object.freeze({ otm: ComponentNode });
const edgeTypes = Object.freeze({});

function docStructureKey(doc: OtmDocument): string {
  return JSON.stringify({
    c: doc.components.map((x) => [x.id, x.name, x.kind]),
    f: doc.data_flows.map((x) => [x.id, x.from_component, x.to_component, x.name]),
  });
}

function ThreatModelDiagramInner({
  document,
  setDocument,
  className = "",
  style,
}: Readonly<{
  document: OtmDocument;
  setDocument: (d: OtmDocument) => void;
  className?: string;
  style?: CSSProperties;
}>) {
  const { t } = useTranslation();
  /** Por omissão: edição activa (drag-and-drop, ligações) — o utilizador pode passar a «Visualizar». */
  const [editMode, setEditMode] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [nodes, setNodes, onNodesChange] = useNodesState([] as Node<OtmNodeData>[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [layoutEpoch, setLayoutEpoch] = useState(0);

  const structureKey = useMemo(() => docStructureKey(document), [document]);

  useEffect(() => {
    setNodes(buildNodes(document, editMode));
    setEdges(buildEdges(document, editMode));
  }, [structureKey, editMode, layoutEpoch, document, setNodes, setEdges]);

  const onConnect = useCallback(
    (conn: Connection) => {
      if (!editMode || !conn.source || !conn.target) return;
      if (conn.source === conn.target) return;
      const exists = document.data_flows.some(
        (f) => f.from_component === conn.source && f.to_component === conn.target,
      );
      if (exists) return;
      const id = `flow_${Date.now()}`;
      const nf: OtmDataFlow = {
        id,
        from_component: conn.source,
        to_component: conn.target,
        name: null,
      };
      setDocument({ ...document, data_flows: [...document.data_flows, nf] });
    },
    [document, setDocument, editMode],
  );

  const onEdgesDelete = useCallback(
    (toRemove: Edge[]) => {
      if (!editMode) return;
      const rm = new Set(toRemove.map((e) => e.id));
      setDocument({
        ...document,
        data_flows: document.data_flows.filter((f) => !rm.has(f.id)),
      });
    },
    [document, setDocument, editMode],
  );

  const onNodesDelete = useCallback(
    (toRemove: Node[]) => {
      if (!editMode) return;
      const rm = new Set(toRemove.map((n) => n.id));
      // Cascades to assets and trust boundaries too — pruning only components and flows
      // leaves references the canonical schema rejects.
      setDocument(removeComponents(document, [...rm]));
      try {
        const cur = loadDiagramLayout();
        for (const id of rm) delete cur[id];
        sessionStorage.setItem("otm.web.diagramLayout", JSON.stringify(cur));
      } catch {
        /* ignore */
      }
    },
    [document, setDocument, editMode],
  );

  const onNodeDragStop = useCallback((_e: unknown, node: Node) => {
    saveDiagramLayoutPatch(node.id, node.position);
  }, []);

  const onSelectionChange = useCallback(({ nodes: sel }: { nodes: Node[] }) => {
    setSelectedId(sel.length === 1 ? sel[0].id : null);
  }, []);

  const selectedComponent = useMemo(
    () => document.components.find((c) => c.id === selectedId) ?? null,
    [document.components, selectedId],
  );

  const updateSelectedLabel = useCallback(
    (name: string) => {
      if (!selectedId || !editMode) return;
      // Grava o nome **tal como foi escrito**. Aqui corria `sanitizeDiagramLabel`, que é um filtro
      // de exibição e é destrutivo por desenho: uma tecla apagava `<…>` do documento canónico
      // ("Customer DB <unencrypted, internet-facing>" -> "Customer DB "), a perda sobrevivia ao
      // reload e seguia para o JSON exportado e para a lista de Componentes, sem undo. E o campo é
      // controlado sobre o `name` cru, por isso o utilizador via a string inteira até ela sumir.
      //
      // Não muda a superfície de XSS: `buildNodes`/`buildEdges` continuam a sanitizar ao desenhar,
      // que é o que a docstring do filtro manda. O controlo real, medido, é o escaping de text
      // node do React mais a CSP — um `<img src=x onerror>` num nome produz zero elementos `<img>`
      // com ou sem este filtro.
      setDocument({
        ...document,
        components: document.components.map((c) =>
          c.id === selectedId ? { ...c, name } : c,
        ),
      });
    },
    [document, selectedId, setDocument, editMode],
  );

  const updateSelectedKind = useCallback(
    (kind: string) => {
      if (!selectedId || !editMode) return;
      setDocument({
        ...document,
        components: document.components.map((c) => (c.id === selectedId ? { ...c, kind } : c)),
      });
    },
    [document, selectedId, setDocument, editMode],
  );

  const addNode = useCallback(() => {
    const id = `n_${Date.now()}`;
    const pos = gridPos(document.components.length);
    saveDiagramLayoutPatch(id, pos);
    setDocument({
      ...document,
      components: [
        ...document.components,
        {
          id,
          name: sanitizeDiagramLabel(t("wizard.newComponentDefault")),
          kind: "process",
        },
      ],
    });
  }, [document, setDocument, t]);

  const removeSelected = useCallback(() => {
    if (!selectedId || !editMode) return;
    const rm = selectedId;
    setDocument(removeComponents(document, [rm]));
    try {
      const cur = loadDiagramLayout();
      delete cur[rm];
      sessionStorage.setItem("otm.web.diagramLayout", JSON.stringify(cur));
    } catch {
      /* ignore */
    }
    setSelectedId(null);
  }, [selectedId, editMode, document, setDocument]);

  const resetLayout = useCallback(() => {
    clearDiagramLayout();
    setLayoutEpoch((e) => e + 1);
  }, []);

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="diagram-mode-toggle"
          className="rounded-full border border-otm-border bg-otm-surface-2 px-3 py-1.5 text-sm font-medium text-otm-text hover:border-otm-border-strong"
          onClick={() => setEditMode((v) => !v)}
        >
          {editMode ? t("diagram.view") : t("diagram.edit")}
        </button>
        {editMode ? (
          <>
            <button
              type="button"
              data-testid="diagram-add-node"
              className="rounded-full border border-otm-border bg-otm-primary-subtle px-3 py-1.5 text-sm font-medium text-otm-accent"
              onClick={addNode}
            >
              {t("diagram.addNode")}
            </button>
            <button
              type="button"
              data-testid="diagram-remove-selected"
              className="rounded-full border border-otm-border px-3 py-1.5 text-sm text-otm-text-muted hover:bg-otm-surface-2 disabled:opacity-40"
              onClick={removeSelected}
              disabled={!selectedId}
            >
              {t("diagram.removeSelected")}
            </button>
            <button
              type="button"
              data-testid="diagram-reset-layout"
              className="rounded-full border border-otm-border px-3 py-1.5 text-sm text-otm-text-muted hover:bg-otm-surface-2"
              onClick={resetLayout}
            >
              {t("diagram.resetLayout")}
            </button>
          </>
        ) : null}
        <label className="ml-2 flex cursor-pointer items-center gap-2 text-xs text-otm-text-muted">
          <input
            type="checkbox"
            checked={showGrid}
            onChange={(e) => setShowGrid(e.target.checked)}
            className="rounded border-otm-border"
          />
          {t("diagram.grid")}
        </label>
      </div>

      <div
        data-testid="threat-model-flow"
        className="h-[min(520px,70vh)] min-h-[360px] w-full rounded-otm-lg border border-otm-border bg-otm-green-950/40"
        style={style}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={editMode ? onConnect : undefined}
          onNodeDragStop={onNodeDragStop}
          onEdgesDelete={editMode ? onEdgesDelete : undefined}
          onNodesDelete={editMode ? onNodesDelete : undefined}
          onSelectionChange={onSelectionChange}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          nodesDraggable={editMode}
          nodesConnectable={editMode}
          elementsSelectable
          deleteKeyCode={editMode ? "Delete" : null}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          {showGrid ? <Background gap={16} size={1} color="rgba(86,255,149,0.12)" /> : null}
          <Controls className="!bg-otm-surface-2 !border-otm-border !shadow-otm-sm" />
          <MiniMap
            className="!bg-otm-surface-2/90 !border-otm-border"
            maskColor="rgba(5,8,7,0.65)"
          />
        </ReactFlow>
      </div>

      {editMode && selectedComponent ? (
        <div className="grid gap-2 rounded-otm-md border border-otm-border bg-otm-surface-1/80 p-3 sm:grid-cols-2">
          <div>
            <label className="text-xs font-medium text-otm-text-muted" htmlFor="dm-label">
              {t("diagram.nameNoHtml")}
            </label>
            <input
              id="dm-label"
              className="mt-1 w-full rounded-otm-md border border-otm-border bg-otm-surface-2 px-2 py-1.5 text-sm text-otm-text"
              value={selectedComponent.name}
              onChange={(e) => updateSelectedLabel(e.target.value)}
              maxLength={120}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-otm-text-muted" htmlFor="dm-kind">
              {t("diagram.kind")}
            </label>
            <select
              id="dm-kind"
              className="mt-1 w-full rounded-otm-md border border-otm-border bg-otm-surface-2 px-2 py-1.5 text-sm text-otm-text"
              value={selectedComponent.kind}
              onChange={(e) => updateSelectedKind(e.target.value)}
            >
              {COMPONENT_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {t(`document.componentKinds.${k.value}`)}
                </option>
              ))}
            </select>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ThreatModelDiagram(
  props: Readonly<{
    document: OtmDocument;
    setDocument: (d: OtmDocument) => void;
    className?: string;
    style?: CSSProperties;
  }>,
) {
  return (
    <ReactFlowProvider>
      <ThreatModelDiagramInner {...props} />
    </ReactFlowProvider>
  );
}
