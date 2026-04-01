import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

export type OtmNodeData = {
  label: string;
  kind: string;
};

function ComponentNodeInner({ data, selected }: NodeProps<OtmNodeData>) {
  return (
    <div
      className={`min-w-[140px] max-w-[200px] rounded-otm-md border bg-otm-surface-2/95 px-3 py-2 shadow-otm-sm transition duration-otm ${
        selected ? "border-otm-accent ring-2 ring-[color:var(--otm-ring)]" : "border-otm-border"
      }`}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-otm-mint-400" />
      <p className="font-mono text-[10px] uppercase tracking-wide text-otm-text-subtle">{data.kind}</p>
      <p className="truncate font-display text-sm font-semibold text-otm-text">{data.label}</p>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-otm-primary" />
    </div>
  );
}

export const ComponentNode = memo(ComponentNodeInner);
