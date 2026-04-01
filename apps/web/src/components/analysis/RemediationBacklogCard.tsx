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
  return (
    <Card
      title="Backlog de remediação (sugerido)"
      subtitle="Priorização heurística com racional — não é gestor de tarefas."
      variant="glass"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" onClick={onLoad} disabled={backlogLoading}>
          {backlogLoading ? "A gerar…" : "Gerar vista de backlog"}
        </Button>
      </div>
      {backlog && (
        <div className="mt-4 space-y-4 text-sm text-otm-text-muted">
          <p>{backlog.executive_summary}</p>
          {backlog.synergy_notes.length > 0 && (
            <div>
              <p className="font-medium text-otm-text">Agrupamentos / sinergia</p>
              <ul className="mt-1 list-inside list-disc text-xs">
                {backlog.synergy_notes.slice(0, 4).map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          )}
          <div>
            <p className="font-medium text-otm-text">Top acções</p>
            <ul className="mt-1 space-y-2">
              {backlog.top_5_action_ids.map((id) => {
                const it = backlog.items.find((x) => x.id === id);
                if (!it) return null;
                return (
                  <li key={id} className="rounded-otm-md border border-otm-border bg-otm-surface-1 px-3 py-2">
                    <span className="font-medium text-otm-text">{it.title}</span>
                    <span className="text-otm-text-subtle">
                      {" "}
                      · {it.priority_label} · esforço {it.effort_estimate}
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
              <p className="font-medium text-otm-text">Quick wins</p>
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
