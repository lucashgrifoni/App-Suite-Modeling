import type { HeuristicThreat } from "../types/api";

export function listFrameworksFromAnalysisThreats(threats: HeuristicThreat[]): string[] {
  const s = new Set<string>();
  for (const h of threats) {
    if (h.skipped_as_duplicate) continue;
    for (const r of h.framework_refs ?? []) s.add(r.framework);
  }
  return [...s].sort((a, b) => a.localeCompare(b));
}

export function filterActiveThreats(
  threats: HeuristicThreat[],
  options: { minScore: number; frameworkFilter?: string },
): HeuristicThreat[] {
  const { minScore, frameworkFilter } = options;
  return threats.filter((h) => {
    if (h.skipped_as_duplicate) return false;
    const score = h.risk.score ?? 0;
    if (score < minScore) return false;
    if (frameworkFilter) {
      const has = (h.framework_refs ?? []).some((r) => r.framework === frameworkFilter);
      if (!has) return false;
    }
    return true;
  });
}

