import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import type { RemediationBacklogResponse } from "../../types/api";

export function RemediationBacklogCard({
  backlog,
  backlogLoading,
  onLoad,
}: Readonly<{
  backlog: RemediationBacklogResponse | null;
  backlogLoading: boolean;
  onLoad: () => void;
}>) {
  const { t } = useTranslation();
  return (
    <Card title={t("remediation.title")} subtitle={t("remediation.subtitle")} variant="glass">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" onClick={onLoad} disabled={backlogLoading}>
          {backlogLoading ? t("remediation.generating") : t("remediation.generateView")}
        </Button>
      </div>
      {backlog && (
        <div className="mt-4 space-y-4 text-sm text-otm-text-muted">
          <p>{backlog.executive_summary}</p>
          {backlog.synergy_notes.length > 0 && (
            <div>
              <p className="font-medium text-otm-text">{t("remediation.synergyTitle")}</p>
              <ul className="mt-1 list-inside list-disc text-xs">
                {backlog.synergy_notes.slice(0, 4).map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          )}
          <div>
            <p className="font-medium text-otm-text">{t("remediation.topActions")}</p>
            <ul className="mt-1 space-y-2">
              {backlog.top_5_action_ids.map((id) => {
                const it = backlog.items.find((x) => x.id === id);
                if (!it) return null;
                return (
                  <li key={id} className="rounded-otm-md border border-otm-border bg-otm-surface-1 px-3 py-2">
                    <span className="font-medium text-otm-text">{it.title}</span>
                    <span className="text-otm-text-subtle">
                      {t("remediation.itemMeta", {
                        priority: it.priority_label,
                        effort: it.effort_estimate,
                      })}
                    </span>
                    {it.explanations?.[0] ? (
                      <p className="mt-1 text-[11px] leading-snug text-otm-text-muted">{it.explanations[0].message}</p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
          {backlog.quick_win_ids.length > 0 && (
            <div>
              <p className="font-medium text-otm-text">{t("remediation.quickWins")}</p>
              <ul className="mt-1 list-inside list-disc text-xs">
                {backlog.quick_win_ids.slice(0, 6).map((id) => {
                  const it = backlog.items.find((x) => x.id === id);
                  return <li key={id}>{it?.title ?? id}</li>;
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
