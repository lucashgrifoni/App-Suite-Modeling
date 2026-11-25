import { memo } from "react";
import { useTranslation } from "react-i18next";
import { WorkspaceIcon, type WorkspaceIconName } from "../ui/WorkspaceIcon";
import { Handle, Position, type NodeProps } from "reactflow";

export type OtmNodeData = {
  label: string;
  kind: string;
  technology?: string | null;
};

const kindIcons: Record<string, WorkspaceIconName> = {
  user: "user",
  process: "process",
  datastore: "asset",
  queue: "list",
  gateway: "flow",
};

function ComponentNodeInner({ data, selected }: NodeProps<OtmNodeData>) {
  const { t } = useTranslation();
  return (
    <div
      className={`min-w-[140px] max-w-[152px] rounded-otm-md border bg-otm-surface-2/95 px-3 py-2 shadow-otm-sm transition duration-otm ${
        selected ? "border-otm-accent ring-2 ring-[color:var(--otm-ring)]" : "border-otm-border"
      }`}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-otm-mint-400" />
      <p className="flex items-center gap-1.5 font-display text-base font-semibold text-otm-text">
        <span className="text-otm-accent">
          <WorkspaceIcon name={kindIcons[data.kind] ?? "box"} />
        </span>
        <span className="truncate">{data.label}</span>
      </p>
      <p className="truncate text-xs text-otm-text-muted">
        {data.technology || t(`document.componentKinds.${data.kind}`, { defaultValue: data.kind })}
      </p>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-otm-primary" />
    </div>
  );
}

export const ComponentNode = memo(ComponentNodeInner);
