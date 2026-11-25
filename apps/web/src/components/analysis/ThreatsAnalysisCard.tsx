import { useState } from "react";
import { ThreatDecision } from "./ThreatDecision";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Label } from "../ui/Label";
import { Select } from "../ui/Select";
import { FrameworkTag } from "../ui/FrameworkTag";
import { FRAMEWORK_LABELS } from "../../constants/frameworkLabels";
import type { HeuristicThreat } from "../../types/api";

export function ThreatsAnalysisCard({
  filtered,
  activeThreatCount,
  minScore,
  onMinScoreChange,
  frameworkFilter,
  onFrameworkFilterChange,
  frameworks,
  onSelectDeclared,
}: Readonly<{
  filtered: HeuristicThreat[];
  activeThreatCount: number;
  minScore: number;
  onMinScoreChange: (n: number) => void;
  frameworkFilter: string;
  onFrameworkFilterChange: (v: string) => void;
  frameworks: string[];
  onSelectDeclared?: (id: string) => void;
}>) {
  const { t } = useTranslation();
  const [selectedId, setSelectedId] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(0);
  const sorted = [...filtered].sort((a, b) => (b.risk.score ?? -1) - (a.risk.score ?? -1));
  const lastPage = Math.max(0, Math.ceil(sorted.length / 6) - 1);
  const current = Math.min(page, lastPage);
  const rows = sorted.slice(current * 6, current * 6 + 6);
  const threat = rows.find((h) => h.id === selectedId) ?? rows[0];
  return (
    <div className="work-split">
      <Card title={t("work.priorities")} subtitle={t("work.sortedRisk")}>
        <Button
          variant="secondary"
          className="mb-3"
          aria-expanded={showFilters}
          onClick={() => setShowFilters(!showFilters)}
        >
          {t("work.filter")}
        </Button>
        {showFilters && (
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="sm:w-48">
              <Label htmlFor="minScore">{t("threatsCard.minScore")}</Label>
              <Input
                id="minScore"
                type="number"
                min={0}
                max={25}
                value={minScore}
                onChange={(e) => {
                  setPage(0);
                  onMinScoreChange(Number(e.target.value) || 0);
                }}
              />
            </div>
            <div className="sm:w-56">
              <Label htmlFor="fw">{t("threatsCard.framework")}</Label>
              <Select
                id="fw"
                value={frameworkFilter}
                onChange={(e) => {
                  setPage(0);
                  onFrameworkFilterChange(e.target.value);
                }}
              >
                <option value="">{t("threatsCard.allFrameworks")}</option>
                {frameworks.map((fw) => (
                  <option key={fw} value={fw}>
                    {FRAMEWORK_LABELS[fw] ?? fw}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        )}
        <p className="mb-3 text-xs text-otm-text-muted">
          {t("threatsCard.showing", { shown: rows.length, total: activeThreatCount })}
        </p>
        <div className="work-list-head grid-cols-[minmax(0,2fr)_minmax(50px,1fr)_auto]">
          <span>{t("work.suggestedThreat")}</span>
          <span>{t("work.target")}</span>
          <span>{t("work.score")}</span>
        </div>
        <ul>
          {rows.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                className="work-select-row grid-cols-[minmax(0,2fr)_minmax(50px,1fr)_auto]"
                aria-pressed={threat?.id === h.id}
                onClick={() => setSelectedId(h.id)}
              >
                <span>
                  <b>
                    {h.title.startsWith(`[${h.stride}]`)
                      ? t(`work.stride.${h.stride}`, { defaultValue: h.title })
                      : h.title}
                  </b>
                  <small>
                    {h.title.startsWith(`[${h.stride}] `)
                      ? h.title.slice(h.stride.length + 3)
                      : h.stride}
                  </small>
                </span>
                <code>{h.target_component_id || h.target_data_flow_id || h.target_asset_id || "—"}</code>
                <span
                  className={`work-score ${(h.risk.score ?? 0) >= 20 ? "critical" : (h.risk.score ?? 0) >= 12 ? "high" : ""}`}
                >
                  {h.risk.score ?? "—"}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {lastPage > 0 && (
          <div className="work-pager">
            <button type="button" disabled={!current} onClick={() => setPage(current - 1)}>
              {t("work.previous")}
            </button>
            {current + 1} / {lastPage + 1}
            <button type="button" disabled={current >= lastPage} onClick={() => setPage(current + 1)}>
              {t("work.next")}
            </button>
          </div>
        )}
        {filtered.length === 0 && (
          // "No threats match the filters" was shown for a model that produced no threats at
          // all — pointing the user at filters they never touched (minimum score at its
          // default 0, no framework chosen) while the real cause was an empty model. With
          // nothing to filter, the filters cannot be the explanation.
          <p className="py-6 text-center text-sm text-otm-text-muted">
            {activeThreatCount === 0 ? t("threatsCard.noneAtAll") : t("threatsCard.noneMatch")}
          </p>
        )}
        <div className="mt-6 flex justify-end border-t border-otm-border pt-4">
          <Link to="/export">
            <Button>{t("export.exportResults")}</Button>
          </Link>
        </div>
      </Card>
      <Card title={t("work.selectedSuggestion")}>
        {threat ? (
          <>
            <h3 className="work-detail-title">
              {threat.title.startsWith(`[${threat.stride}]`)
                ? t(`work.stride.${threat.stride}`, { defaultValue: threat.title })
                : threat.title}
            </h3>
            {threat.title.startsWith(`[${threat.stride}]`) && (
              <p className="work-muted">{threat.title}</p>
            )}
            <p className="work-muted">{threat.description}</p>
            <dl className="work-facts">
              <div>
                <dt>{t("work.target")}</dt>
                <dd>
                  {threat.target_component_id ||
                    threat.target_data_flow_id ||
                    threat.target_asset_id ||
                    "—"}
                </dd>
              </div>
              <div>
                <dt>{t("work.likelihood")}</dt>
                <dd>{threat.risk.likelihood ?? "—"}</dd>
              </div>
              <div>
                <dt>{t("work.impact")}</dt>
                <dd>{threat.risk.impact ?? "—"}</dd>
              </div>
              <div>
                <dt>{t("work.score")}</dt>
                <dd>{threat.risk.score ?? "—"}</dd>
              </div>
            </dl>
            {!!threat.framework_refs?.length && (
              <div className="flex flex-wrap gap-1">
                {threat.framework_refs.map((r) => (
                  <FrameworkTag
                    key={`${r.framework}:${r.control_id}`}
                    label={`${FRAMEWORK_LABELS[r.framework] ?? r.framework}:${r.control_id}`}
                  />
                ))}
              </div>
            )}
            <ThreatDecision key={threat.id} suggestion={threat} onSelectDeclared={onSelectDeclared} />
          </>
        ) : (
          <p className="work-muted">—</p>
        )}
      </Card>
    </div>
  );
}
