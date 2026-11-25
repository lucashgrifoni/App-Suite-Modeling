import { useId } from "react";
import { useTranslation } from "react-i18next";
import type { OtmDocument } from "../../types/document";
import { boundaryBoxes, initialPositions } from "../../utils/diagramTopology";

export function TopologyPreview({ document: doc }: Readonly<{ document: OtmDocument }>) {
  const { t } = useTranslation();
  const marker = useId();
  const components = doc.components.slice(0, 4);
  const preview = { ...doc, components };
  const positions = initialPositions(preview);
  const nodes = components.map((c) => ({
    ...c,
    position: positions.get(c.id)!,
    width: 136,
    height: 53,
  }));
  const bounds = boundaryBoxes(preview, nodes);
  const width = Math.max(220, ...nodes.map((n) => n.position.x + n.width + 29));
  const flows = doc.data_flows.filter(
    (f) => positions.has(f.from_component) && positions.has(f.to_component),
  );
  return (
    <figure className="work-summary-graph">
      {nodes.length ? (
        <svg
          className="topology-preview"
          viewBox={`0 0 ${width} 157`}
          aria-label={t("work.topology")}
          role="img"
        >
          <defs>
            <marker
              id={marker}
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M0 0L10 5L0 10Z" fill="var(--otm-primary-ink)" />
            </marker>
          </defs>
          {bounds.map((b) => (
            <g key={b.id}>
              <rect
                className="preview-boundary"
                x={b.x}
                y={b.y}
                width={b.width}
                height={b.height}
                rx="9"
              />
              <svg x={b.x + 9} y={b.y + 6} width={b.width - 18} height="27">
                <text y="18">{b.name}</text>
              </svg>
            </g>
          ))}
          {flows.map((f) => {
            const from = positions.get(f.from_component)!,
              to = positions.get(f.to_component)!;
            const direct = to.x > from.x && to.x - from.x < 250;
            const edge = direct
              ? `M${from.x + 136} 91 H${to.x - 2}`
              : `M${from.x + 94} 117 Q${from.x + 102} 149 ${(from.x + to.x) / 2 + 68} 141 T${to.x + 39} 118`;
            return (
              <path
                key={f.id}
                d={edge}
                fill="none"
                stroke="var(--otm-primary-ink)"
                strokeWidth="2"
                markerEnd={`url(#${marker})`}
              >
                <title>
                  {f.from_component} → {f.to_component} · {f.protocol || f.name || f.id}
                </title>
              </path>
            );
          })}
          {nodes.map((n) => (
            <g key={n.id} transform={`translate(${n.position.x} ${n.position.y})`}>
              <rect className="preview-node" width={n.width} height={n.height} rx="7" />
              <title>{n.name}</title>
              <svg x="9" y="4" width={n.width - 18} height="45">
                <text y="18" className="preview-name">
                  {n.name}
                </text>
                <text y="37">
                  {n.technology || t(`document.componentKinds.${n.kind}`, { defaultValue: n.kind })}
                </text>
              </svg>
            </g>
          ))}
        </svg>
      ) : (
        <p className="work-muted">{t("work.noComponents")}</p>
      )}
      <figcaption>
        {nodes.length < doc.components.length
          ? t("work.previewCount", { shown: nodes.length, total: doc.components.length })
          : t("work.topology")}
      </figcaption>
    </figure>
  );
}
