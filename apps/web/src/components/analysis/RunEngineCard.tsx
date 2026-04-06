import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Label } from "../ui/Label";
import { Select } from "../ui/Select";
import { MethodologyBadge } from "../ui/MethodologyBadge";
import type { MethodologyRecommendation } from "../../types/api";
import type { MethodologyId } from "../../types/methodology";

export function RunEngineCard({
  methodology,
  onMethodologyChange,
  packId,
  onPackIdChange,
  loading,
  recommending,
  recommendation,
  onRun,
  onRecommend,
}: Readonly<{
  methodology: MethodologyId;
  onMethodologyChange: (m: MethodologyId) => void;
  packId: string;
  onPackIdChange: (v: string) => void;
  loading: boolean;
  recommending: boolean;
  recommendation: MethodologyRecommendation | null;
  onRun: () => void;
  onRecommend: () => void;
}>) {
  const { t } = useTranslation();

  return (
    <Card title={t("runEngine.title")} subtitle={t("runEngine.subtitle")} variant="glass">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:gap-4">
        <div className="min-w-0 flex-1 space-y-3 lg:max-w-md">
          <Label htmlFor="methodology">{t("runEngine.methodology")}</Label>
          <Select
            id="methodology"
            value={methodology}
            onChange={(e) => onMethodologyChange(e.target.value as MethodologyId)}
          >
            <option value="stride">{t("runEngine.optStride")}</option>
            <option value="linddun">{t("runEngine.optLinddun")}</option>
            <option value="nist_data_centric">{t("runEngine.optNist")}</option>
            <option value="octave_allegro">{t("runEngine.optOctave")}</option>
            <option value="cia_die">{t("runEngine.optCia")}</option>
            <option value="pasta">{t("runEngine.optPasta")}</option>
            <option value="plot4ai">{t("runEngine.optPlot4ai")}</option>
          </Select>
          <p className="text-xs text-otm-text-muted">{t(`methodologyMeta.${methodology}.hint`)}</p>
          <div className="flex flex-wrap gap-2">
            <MethodologyBadge id={methodology} />
            <span className="rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] text-otm-text-muted">
              {t("runEngine.category")} {t(`methodologyMeta.${methodology}.category`)}
            </span>
            <span className="rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] text-otm-text-muted">
              {t("runEngine.bestFor")} {t(`methodologyMeta.${methodology}.bestFor`)}
            </span>
            <span className="rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] text-otm-text-muted">
              {t("runEngine.maturity")} {t(`methodologyMeta.${methodology}.maturity`)}
            </span>
          </div>
          <p className="text-xs text-otm-text-muted">{t("runEngine.overrideHint")}</p>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <Label htmlFor="pack">{t("runEngine.pack")}</Label>
          <Input
            id="pack"
            placeholder={t("runEngine.packPlaceholder")}
            value={packId}
            onChange={(e) => onPackIdChange(e.target.value)}
          />
          <p className="text-xs text-otm-text-muted">{t("runEngine.packEmptyHint")}</p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
          <Button variant="secondary" onClick={onRecommend} disabled={recommending}>
            {recommending ? t("runEngine.recommending") : t("runEngine.recommend")}
          </Button>
          <Button onClick={onRun} disabled={loading}>
            {loading ? t("runEngine.running") : t("runEngine.run")}
          </Button>
        </div>
      </div>
      {recommendation && (
        <div className="mt-4 rounded-otm-md border border-otm-border-strong bg-otm-primary-subtle p-4 text-sm text-otm-text">
          <p className="font-medium text-otm-accent">
            {t("runEngine.recTitle", { methodology: recommendation.methodology })}
          </p>
          <p className="mt-1 text-otm-text-muted">{recommendation.reason}</p>
          {recommendation.explanations && recommendation.explanations.length > 0 ? (
            <details className="mt-2 text-xs text-otm-text-muted">
              <summary className="cursor-pointer font-medium text-otm-text">{t("runEngine.recContext")}</summary>
              <ul className="mt-1 list-inside list-disc">
                {recommendation.explanations.slice(0, 4).map((e) => (
                  <li key={e.id}>{e.message}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      )}
    </Card>
  );
}
