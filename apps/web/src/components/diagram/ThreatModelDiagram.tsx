import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  useStore,
  type Connection,
  type Edge,
  type Node,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { BoundaryOverlay } from "./BoundaryOverlay";
import { boundaryFor, initialPositions } from "../../utils/diagramTopology";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { ComponentNode, type OtmNodeData } from "./ComponentNode";
import { sanitizeDiagramLabel } from "../../utils/diagramSanitize";
import { removeComponents } from "../../utils/documentNormalize";
import {
  clearDiagramLayout,
  documentLayoutKey,
  loadDiagramLayout,
  removeDiagramLayoutEntries,
  saveDiagramLayoutPatch,
} from "../../utils/diagramLayoutStorage";
import { COMPONENT_KINDS, type OtmDataFlow, type OtmDocument } from "../../types/document";

function buildNodes(doc: OtmDocument, editMode: boolean): Node<OtmNodeData>[] {
  const layout = loadDiagramLayout(documentLayoutKey(doc));
  const positions = initialPositions(doc);
  return doc.components.map((c) => ({
    id: c.id,
    type: "otm",
    position: layout[c.id] ?? positions.get(c.id)!,
    data: { label: sanitizeDiagramLabel(c.name), kind: c.kind, technology: c.technology },
    draggable: editMode,
    selectable: true,
    deletable: editMode,
  }));
}

// Module-scoped marker config so each edge reuses the same object reference and
// React Flow's prop-stability heuristic does not flag the diagram on re-render.
const EDGE_MARKER_END = { type: MarkerType.ArrowClosed, color: "var(--otm-primary-ink)" } as const;

function buildEdges(doc: OtmDocument, editMode: boolean): Edge[] {
  return doc.data_flows.map((f) => ({
    id: f.id,
    source: f.from_component,
    target: f.to_component,
    label: sanitizeDiagramLabel(f.name || f.protocol || "") || undefined,
    markerEnd: EDGE_MARKER_END,
    deletable: editMode,
  }));
}

// Keep custom renderers stable between renders.
const nodeTypes = Object.freeze({ otm: ComponentNode });
const fitOptions = { padding: 0.17, maxZoom: 1.2 };

function ThreatModelDiagramInner({
  document,
  setDocument,
  renderInventory,
  className = "",
  style,
}: Readonly<{
  document: OtmDocument;
  setDocument: (d: OtmDocument) => void;
  renderInventory: (selectComponent: (id: string) => void, inspectedId?: string) => ReactNode;
  className?: string;
  style?: CSSProperties;
}>) {
  const { t } = useTranslation();
  /** Por omissão: edição activa (drag-and-drop, ligações) — o utilizador pode passar a «Visualizar». */
  const [editMode, setEditMode] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [showMap, setShowMap] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([] as Node<OtmNodeData>[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [layoutEpoch, setLayoutEpoch] = useState(0);

  const width = useStore((state) => state.width);
  const previousWidth = useRef(0);
  const { fitView } = useReactFlow();
  useEffect(() => {
    const previous = previousWidth.current;
    previousWidth.current = width;
    if (!previous || !width || previous === width) return;
    const frame = requestAnimationFrame(() => {
      void fitView(fitOptions);
    });
    return () => cancelAnimationFrame(frame);
  }, [width, fitView]);

  useEffect(() => {
    setNodes((previous) => {
      const selection = new Set(previous.filter((node) => node.selected).map((node) => node.id));
      return buildNodes(document, editMode).map((node) => ({
        ...node,
        selected: selection.has(node.id),
      }));
    });
    setEdges(buildEdges(document, editMode));
  }, [editMode, layoutEpoch, document, setNodes, setEdges]);

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
      removeDiagramLayoutEntries(documentLayoutKey(document), [...rm]);
    },
    [document, setDocument, editMode],
  );

  const onNodeDragStop = useCallback(
    (_e: unknown, node: Node) => {
      saveDiagramLayoutPatch(documentLayoutKey(document), node.id, node.position);
    },
    [document],
  );

  const onSelectionChange = useCallback(({ nodes: sel }: { nodes: Node[] }) => {
    setSelectedId(sel.length === 1 ? sel[0].id : null);
  }, []);

  function selectComponent(id: string) {
    setNodes((current) => current.map((node) => ({ ...node, selected: node.id === id })));
  }

  const selectedComponent = useMemo(
    () => document.components.find((c) => c.id === selectedId) ?? null,
    [document.components, selectedId],
  );

  const inspected =
    selectedComponent ?? document.components.find((c) => c.kind === "process") ?? document.components[0];
  const relatedFlows = inspected
    ? document.data_flows.filter(
        (f) => f.from_component === inspected.id || f.to_component === inspected.id,
      )
    : [];
  const relatedAssets = inspected
    ? document.assets.filter(
        (a) => a.related_component_ids?.includes(inspected.id) || inspected.asset_ids?.includes(a.id),
      )
    : [];
  const componentNames = new Map(document.components.map((c) => [c.id, c.name]));

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
        components: document.components.map((c) => (c.id === selectedId ? { ...c, name } : c)),
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
    removeDiagramLayoutEntries(documentLayoutKey(document), [rm]);
    setSelectedId(null);
  }, [selectedId, editMode, document, setDocument]);

  const resetLayout = useCallback(() => {
    clearDiagramLayout();
    setLayoutEpoch((e) => e + 1);
  }, []);

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="work-split diagram-split">
        <Card className="diagram-canvas">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-lg font-semibold">{t("work.topology")}</h2>
            <div className="work-mode" role="group" aria-label={t("work.diagramMode")}>
              {[true, false].map((edit) => (
                <button
                  key={String(edit)}
                  type="button"
                  aria-pressed={editMode === edit}
                  data-testid={editMode !== edit ? "diagram-mode-toggle" : undefined}
                  onClick={() => setEditMode(edit)}
                >
                  {t(edit ? "diagram.edit" : "diagram.view")}
                </button>
              ))}
            </div>
          </div>

          <div
            data-testid="threat-model-flow"
            className="h-[clamp(260px,38vh,420px)] w-full rounded-otm-md border border-otm-border bg-otm-surface-2"
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
              nodesDraggable={editMode}
              nodesConnectable={editMode}
              elementsSelectable
              deleteKeyCode={editMode ? "Delete" : null}
              fitView
              fitViewOptions={fitOptions}
              minZoom={0.08}
              proOptions={{ hideAttribution: true }}
            >
              <BoundaryOverlay document={document} nodes={nodes} />
              {showGrid ? <Background gap={16} size={1} color="var(--otm-border-strong)" /> : null}
              <Controls
                showInteractive={false}
                className="!bg-otm-surface-2 !border-otm-border !shadow-otm-sm"
              />
              {showMap && (
                <MiniMap
                  style={{ width: 120, height: 72, backgroundColor: "var(--otm-surface-2)" }}
                  nodeColor="var(--otm-primary-ink)"
                  className="border-otm-border!"
                  maskColor="var(--otm-primary-subtle)"
                />
              )}
            </ReactFlow>
          </div>

          <div className="work-legend">
            <span>{t("work.dataFlow")}</span>
            <span>{t("work.trustBoundary")}</span>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-otm-border pt-3">
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
            <label className="flex items-center gap-2 text-xs text-otm-text-muted">
              <input type="checkbox" checked={showMap} onChange={(e) => setShowMap(e.target.checked)} />
              {t("work.minimap")}
            </label>
          </div>
        </Card>
        <Card title={t("work.inspector")} className="diagram-inspector">
          {inspected ? (
            <>
              <h3 className="work-detail-title">{inspected.name}</h3>
              <p className="work-muted">
                {t(`document.componentKinds.${inspected.kind}`, { defaultValue: inspected.kind })} ·{" "}
                <code>{inspected.id}</code>
              </p>
              {inspected.description && <p className="work-muted">{inspected.description}</p>}
              <dl className="work-facts">
                <div>
                  <dt>{t("work.trustBoundary")}</dt>
                  <dd>
                    {boundaryFor(document, inspected.id, inspected.in_trust_boundary)?.name ?? "—"}
                  </dd>
                </div>
                {inspected.technology && (
                  <div>
                    <dt>{t("work.technology")}</dt>
                    <dd>{inspected.technology}</dd>
                  </div>
                )}
                {inspected.responsibility && (
                  <div>
                    <dt>{t("work.responsibility")}</dt>
                    <dd>{inspected.responsibility}</dd>
                  </div>
                )}
              </dl>
              <h4>{t("work.relatedFlows")}</h4>
              <ul className="work-related">
                {relatedFlows.map((f) => (
                  <li key={f.id}>
                    <b>
                      {componentNames.get(f.from_component) ?? f.from_component} →{" "}
                      {componentNames.get(f.to_component) ?? f.to_component}
                    </b>
                    <small>{f.protocol || f.name || f.id}</small>
                  </li>
                ))}
              </ul>
              {!relatedFlows.length && <p className="work-muted">—</p>}
              <h4>{t("work.relatedAssets")}</h4>
              <p className="work-muted">{relatedAssets.map((a) => a.name).join(" · ") || "—"}</p>
              {!selectedComponent && editMode && (
                <Button
                  variant="secondary"
                  className="mt-3"
                  onClick={() => selectComponent(inspected.id)}
                >
                  {t("work.editComponent")}
                </Button>
              )}
            </>
          ) : (
            <p className="work-muted">{t("work.noComponents")}</p>
          )}
          {editMode && selectedComponent ? (
            <div className="grid gap-2 rounded-otm-md border border-otm-border p-3 sm:grid-cols-2">
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
        </Card>
        {renderInventory(selectComponent, inspected?.id)}
      </div>
    </div>
  );
}

export function ThreatModelDiagram(
  props: Readonly<{
    document: OtmDocument;
    setDocument: (d: OtmDocument) => void;
    renderInventory: (selectComponent: (id: string) => void, inspectedId?: string) => ReactNode;
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
