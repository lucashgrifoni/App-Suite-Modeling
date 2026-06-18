import { describe, expect, it } from "vitest";
import type { HeuristicThreat } from "../types/api";
import { filterActiveThreats, listFrameworksFromAnalysisThreats } from "./analysisFilters";

function threat(opts: { score?: number; frameworks?: string[]; duplicate?: boolean } = {}): HeuristicThreat {
  return {
    risk: { score: opts.score ?? 0 },
    framework_refs: (opts.frameworks ?? []).map((framework) => ({ framework })),
    skipped_as_duplicate: opts.duplicate ?? false,
  } as unknown as HeuristicThreat;
}

describe("listFrameworksFromAnalysisThreats", () => {
  it("collects unique framework ids, sorted, skipping duplicate threats", () => {
    const threats = [
      threat({ frameworks: ["NIST CSF", "OWASP ASVS"] }),
      threat({ frameworks: ["NIST CSF"] }),
      threat({ duplicate: true, frameworks: ["ZZZ Only In Duplicate"] }),
    ];
    expect(listFrameworksFromAnalysisThreats(threats)).toEqual(["NIST CSF", "OWASP ASVS"]);
  });

  it("returns an empty list when there are no threats", () => {
    expect(listFrameworksFromAnalysisThreats([])).toEqual([]);
  });
});

describe("filterActiveThreats", () => {
  const threats = [
    threat({ score: 1 }),
    threat({ score: 9, frameworks: ["STRIDE"] }),
    threat({ score: 20, duplicate: true }),
  ];

  it("drops threats below minScore and duplicates", () => {
    const result = filterActiveThreats(threats, { minScore: 5 });
    expect(result).toHaveLength(1);
    expect(result[0].risk.score).toBe(9);
  });

  it("keeps only threats matching the framework filter", () => {
    expect(filterActiveThreats(threats, { minScore: 0, frameworkFilter: "STRIDE" })).toHaveLength(1);
    expect(filterActiveThreats(threats, { minScore: 0, frameworkFilter: "NOT-PRESENT" })).toHaveLength(0);
  });

  it("treats a missing score as 0", () => {
    const noScore = [threat({ frameworks: ["X"] })];
    expect(filterActiveThreats(noScore, { minScore: 1 })).toHaveLength(0);
    expect(filterActiveThreats(noScore, { minScore: 0 })).toHaveLength(1);
  });
});
