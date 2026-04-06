import { useTranslation } from "react-i18next";
import { Label } from "../ui/Label";
import { Select } from "../ui/Select";
import type { AnalysisResult } from "../../types/api";

export function ExplanationsSection({
  analysis,
  explanationCategoryFilter,
  onExplanationCategoryChange,
  visibleExplanations,
  explanationCategories,
}: Readonly<{
  analysis: AnalysisResult;
  explanationCategoryFilter: string;
  onExplanationCategoryChange: (v: string) => void;
  visibleExplanations: NonNullable<AnalysisResult["explanations"]>;
  explanationCategories: string[];
}>) {
  const { t } = useTranslation();
  if (!analysis.explanations?.length) return null;
  return (
    <details className="rounded-otm-lg border border-otm-border bg-otm-surface-2/80 p-4 text-sm text-otm-text">
      <summary className="cursor-pointer font-medium">{t("explanations.sectionTitle")}</summary>
      <p className="mt-2 text-xs text-otm-text-muted">{t("explanations.sectionBody")}</p>
      <div className="mt-2 max-w-xs">
        <Label htmlFor="expCategory">{t("explanations.category")}</Label>
        <Select
          id="expCategory"
          value={explanationCategoryFilter}
          onChange={(e) => onExplanationCategoryChange(e.target.value)}
        >
          <option value="">{t("explanations.allCategories")}</option>
          {explanationCategories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </Select>
      </div>
      <ul className="mt-2 space-y-1.5 text-xs text-otm-text-muted">
        {visibleExplanations.slice(0, 8).map((e) => (
          <li key={e.id}>
            <span className="font-medium text-otm-text">{e.subject}:</span> {e.message}
          </li>
        ))}
      </ul>
      {visibleExplanations.length === 0 ? (
        <p className="mt-2 text-xs text-otm-text-subtle">{t("explanations.emptyCategory")}</p>
      ) : null}
    </details>
  );
}
