import { memo } from "react";
import { Link } from "react-router-dom";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Label } from "../ui/Label";
import { Select } from "../ui/Select";
import { Badge } from "../ui/Badge";
import { FrameworkTag } from "../ui/FrameworkTag";
import { RiskScoreBar } from "../analytics/RiskScoreBar";
import { FRAMEWORK_LABELS } from "../../constants/frameworkLabels";
import type { HeuristicThreat } from "../../types/api";

const ThreatRow = memo(function ThreatRow({ h }: Readonly<{ h: HeuristicThreat }>) {
  const sc = h.risk.score;
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-otm-text">{h.title}</p>
          <p className="mt-0.5 text-xs text-otm-text-muted">
            {h.target_component_id && <>Componente: {h.target_component_id} · </>}
            {h.target_data_flow_id && <>Fluxo: {h.target_data_flow_id} · </>}
            STRIDE: {h.stride}
          </p>
        </div>
        <div className="flex w-full min-w-[140px] max-w-[200px] flex-col items-end gap-1 sm:w-auto">
          <Badge tone="warn">L×I {sc ?? "—"}</Badge>
          {typeof sc === "number" ? <RiskScoreBar score={sc} variant="compact" className="w-full" /> : null}
        </div>
      </div>
      {(h.framework_refs?.length ?? 0) > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {(h.framework_refs ?? []).map((r) => (
            <FrameworkTag
              key={`${h.id}:${r.framework}:${r.control_id}`}
              label={`${FRAMEWORK_LABELS[r.framework] ?? r.framework}:${r.control_id}`}
            />
          ))}
        </div>
      )}
    </li>
  );
});

export function ThreatsAnalysisCard({
  filtered,
  activeThreatCount,
  minScore,
  onMinScoreChange,
  frameworkFilter,
  onFrameworkFilterChange,
  frameworks,
}: Readonly<{
  filtered: HeuristicThreat[];
  activeThreatCount: number;
  minScore: number;
  onMinScoreChange: (n: number) => void;
  frameworkFilter: string;
  onFrameworkFilterChange: (v: string) => void;
  frameworks: string[];
}>) {
  return (
    <Card
      title="Ameaças sugeridas"
      subtitle="Filtre por pontuação ou por catálogo de framework."
      variant="glass"
    >
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="sm:w-48">
          <Label htmlFor="minScore">Pontuação mínima (L×I)</Label>
          <Input
            id="minScore"
            type="number"
            min={0}
            max={25}
            value={minScore}
            onChange={(e) => onMinScoreChange(Number(e.target.value) || 0)}
          />
        </div>
        <div className="sm:w-56">
          <Label htmlFor="fw">Framework</Label>
          <Select id="fw" value={frameworkFilter} onChange={(e) => onFrameworkFilterChange(e.target.value)}>
            <option value="">Todos</option>
            {frameworks.map((fw) => (
              <option key={fw} value={fw}>
                {FRAMEWORK_LABELS[fw] ?? fw}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <p className="mb-3 text-xs text-otm-text-muted">
        A mostrar {filtered.length} de {activeThreatCount} ameaças ativas.
      </p>
      <ul className="divide-y divide-otm-border">
        {filtered.map((h) => (
          <ThreatRow key={h.id} h={h} />
        ))}
      </ul>
      {filtered.length === 0 && (
        <p className="py-6 text-center text-sm text-otm-text-muted">Nenhuma ameaça corresponde aos filtros.</p>
      )}
      <div className="mt-6 flex justify-end border-t border-otm-border pt-4">
        <Link to="/export">
          <Button>Exportar resultados</Button>
        </Link>
      </div>
    </Card>
  );
}
