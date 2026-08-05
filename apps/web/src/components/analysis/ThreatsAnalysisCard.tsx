import { memo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
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
  const { t } = useTranslation();
  const sc = h.risk.score;
  const scoreLabel = sc == null ? "—" : String(sc);
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-otm-text">{h.title}</p>
          <p className="mt-0.5 text-xs text-otm-text-muted">
            {h.target_component_id && (
              <>
                {t("threatsCard.component")} {h.target_component_id} ·{" "}
              </>
            )}
            {h.target_data_flow_id && (
              <>
                {t("threatsCard.flow")} {h.target_data_flow_id} ·{" "}
              </>
            )}
            {t("threatsCard.stride")} {h.stride}
          </p>
        </div>
        <div className="flex w-full min-w-[140px] max-w-[200px] flex-col items-end gap-1 sm:w-auto">
          <Badge tone="warn">{t("threatsCard.liScore", { score: scoreLabel })}</Badge>
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
  const { t } = useTranslation();
  return (
    <Card
      title={t("threatsCard.title")}
      subtitle={t("threatsCard.subtitle")}
      variant="glass"
    >
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="sm:w-48">
          <Label htmlFor="minScore">{t("threatsCard.minScore")}</Label>
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
          <Label htmlFor="fw">{t("threatsCard.framework")}</Label>
          <Select id="fw" value={frameworkFilter} onChange={(e) => onFrameworkFilterChange(e.target.value)}>
            <option value="">{t("threatsCard.allFrameworks")}</option>
            {frameworks.map((fw) => (
              <option key={fw} value={fw}>
                {FRAMEWORK_LABELS[fw] ?? fw}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <p className="mb-3 text-xs text-otm-text-muted">
        {t("threatsCard.showing", { shown: filtered.length, total: activeThreatCount })}
      </p>
      <ul className="divide-y divide-otm-border">
        {filtered.map((h) => (
          <ThreatRow key={h.id} h={h} />
        ))}
      </ul>
      {filtered.length === 0 && (
        <p className="py-6 text-center text-sm text-otm-text-muted">{t("threatsCard.noneMatch")}</p>
      )}
      <div className="mt-6 flex justify-end border-t border-otm-border pt-4">
        <Link to="/export">
          <Button>{t("export.exportResults")}</Button>
        </Link>
      </div>
    </Card>
  );
}
