import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Label } from "../ui/Label";
import { Select } from "../ui/Select";
import { MethodologyBadge } from "../ui/MethodologyBadge";
import { METHODOLOGY_META } from "../../constants/methodologyMeta";
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
  const meta = METHODOLOGY_META[methodology];

  return (
    <Card title="Executar motor" subtitle="Metodologia, pack opcional e execução do motor." variant="glass">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:gap-4">
        <div className="min-w-0 flex-1 space-y-3 lg:max-w-md">
          <Label htmlFor="methodology">Metodologia</Label>
          <Select
            id="methodology"
            value={methodology}
            onChange={(e) => onMethodologyChange(e.target.value as MethodologyId)}
          >
            <option value="stride">STRIDE (default)</option>
            <option value="linddun">LINDDUN (privacidade)</option>
            <option value="nist_data_centric">NIST Data-Centric</option>
            <option value="octave_allegro">OCTAVE Allegro</option>
            <option value="cia_die">CIA / CIA-DIE</option>
            <option value="pasta">PASTA (avançado/risk-centric)</option>
            <option value="plot4ai">PLOT4ai (AI/LLM)</option>
          </Select>
          <p className="text-xs text-otm-text-muted">{meta.hint}</p>
          <div className="flex flex-wrap gap-2">
            <MethodologyBadge id={methodology} />
            <span className="rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] text-otm-text-muted">
              Category: {meta.category}
            </span>
            <span className="rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] text-otm-text-muted">
              Best for: {meta.bestFor}
            </span>
            <span className="rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] text-otm-text-muted">
              Maturity: {meta.maturity}
            </span>
          </div>
          <p className="text-xs text-otm-text-muted">
            Pode recomendar automaticamente e ainda assim fazer override manual.
          </p>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <Label htmlFor="pack">Industry pack (opcional)</Label>
          <Input
            id="pack"
            placeholder="ex.: finance"
            value={packId}
            onChange={(e) => onPackIdChange(e.target.value)}
          />
          <p className="text-xs text-otm-text-muted">Deixe vazio para análise só com heurísticas base.</p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
          <Button variant="secondary" onClick={onRecommend} disabled={recommending}>
            {recommending ? "A recomendar…" : "Recomendar metodologia"}
          </Button>
          <Button onClick={onRun} disabled={loading}>
            {loading ? "A analisar…" : "Gerar análise"}
          </Button>
        </div>
      </div>
      {recommendation && (
        <div className="mt-4 rounded-otm-md border border-otm-border-strong bg-otm-primary-subtle p-4 text-sm text-otm-text">
          <p className="font-medium text-otm-accent">Recomendação: {recommendation.methodology}</p>
          <p className="mt-1 text-otm-text-muted">{recommendation.reason}</p>
          {recommendation.explanations && recommendation.explanations.length > 0 ? (
            <details className="mt-2 text-xs text-otm-text-muted">
              <summary className="cursor-pointer font-medium text-otm-text">Contexto da recomendação</summary>
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
