import { useTranslation } from "react-i18next";
import type { OtmDocument } from "../../types/document";
import { Card } from "../ui/Card";
import { WorkspaceIcon, type WorkspaceIconName } from "../ui/WorkspaceIcon";

export function WorkspaceStat({
  icon,
  label,
  value,
  hint,
}: Readonly<{
  icon: WorkspaceIconName;
  label: string;
  value: number | string;
  hint?: string;
}>) {
  return (
    <div className="work-stat">
      <span>
        <WorkspaceIcon name={icon} />
        {label}
      </span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}

export function ModelSummary({ document }: Readonly<{ document: OtmDocument }>) {
  const { t } = useTranslation();
  return (
    <Card title={t("work.sessionModel")}>
      <h3 className="font-display text-lg font-semibold">{document.metadata.title}</h3>
      <dl className="work-facts">
        {document.metadata.owner && (
          <div>
            <dt>{t("work.owner")}</dt>
            <dd>{document.metadata.owner}</dd>
          </div>
        )}
        <div>
          <dt>{t("review.componentsTitle")}</dt>
          <dd>{document.components.length}</dd>
        </div>
        <div>
          <dt>{t("review.flowsTitle")}</dt>
          <dd>{document.data_flows.length}</dd>
        </div>
        <div>
          <dt>{t("review.assetsTitle")}</dt>
          <dd>{document.assets.length}</dd>
        </div>
      </dl>
    </Card>
  );
}
