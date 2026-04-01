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
  if (!analysis.explanations?.length) return null;
  return (
    <details className="rounded-otm-lg border border-otm-border bg-otm-surface-2/80 p-4 text-sm text-otm-text">
      <summary className="cursor-pointer font-medium">Explicabilidade do resultado</summary>
      <p className="mt-2 text-xs text-otm-text-muted">
        Motivos estruturados gerados pelo motor (máx. 8 linhas; o JSON completo tem o resto).
      </p>
      <div className="mt-2 max-w-xs">
        <Label htmlFor="expCategory">Categoria</Label>
        <Select
          id="expCategory"
          value={explanationCategoryFilter}
          onChange={(e) => onExplanationCategoryChange(e.target.value)}
        >
          <option value="">Todas</option>
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
        <p className="mt-2 text-xs text-otm-text-subtle">Sem explicações para esta categoria.</p>
      ) : null}
    </details>
  );
}
