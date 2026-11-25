import { useMemo } from "react";
import { boundaryBoxes } from "../../utils/diagramTopology";
import { useStore, type Node } from "reactflow";
import type { OtmDocument } from "../../types/document";
import { sanitizeDiagramLabel } from "../../utils/diagramSanitize";

export function BoundaryOverlay({
  document,
  nodes,
}: Readonly<{ document: OtmDocument; nodes: Node[] }>) {
  const [x, y, zoom] = useStore((s) => s.transform);
  const bounds = useMemo(() => boundaryBoxes(document, nodes), [document, nodes]);
  return (
    <svg className="boundary-overlay" aria-hidden="true">
      <g transform={`translate(${x} ${y}) scale(${zoom})`}>
        {bounds.map((b) => (
          <g key={b.id} data-boundary-id={b.id}>
            <rect x={b.x} y={b.y} width={b.width} height={b.height} rx="10" />
            <svg x={b.x + 12} y={b.y + 6} width={Math.max(1, b.width - 24)} height="25">
              <text y="17">{sanitizeDiagramLabel(b.name)}</text>
            </svg>
          </g>
        ))}
      </g>
    </svg>
  );
}
