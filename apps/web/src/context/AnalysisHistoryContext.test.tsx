/**
 * A history snapshot must record the analysis the run that triggered it produced.
 *
 * `AnalysisPage.run()` does `setAnalysis(r)` and then `appendSnapshot("analysis")` in the
 * same event handler. React has not re-rendered at that point, so an `appendSnapshot` that
 * read the session `analysis` out of its own closure saw the *previous* value — `null` on
 * the first run of a session, and the run-before-last's analysis afterwards. The stored
 * entry then claimed `analysis: null` / `maxScore: null`, History rendered "0 threats", the
 * snapshot PDF said "Analysis not available", and restoring the entry wiped the session
 * analysis that was on screen.
 *
 * The fix is an explicit argument: the caller hands `appendSnapshot` the analysis the
 * snapshot is *of*, so the entry never depends on React's commit timing.
 */

import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { AnalysisHistoryProvider, useAnalysisHistory } from "./AnalysisHistoryContext";
import { SessionProvider, useSession } from "./SessionContext";
import { loadHistory } from "../utils/analysisHistoryStorage";
import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";

function wrapper({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <SessionProvider>
      <AnalysisHistoryProvider>{children}</AnalysisHistoryProvider>
    </SessionProvider>
  );
}

function makeDoc(title: string, componentId?: string): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "api_backend",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title, tags: [] },
    components: componentId ? [{ id: componentId, name: componentId, kind: "process" }] : [],
    data_flows: [],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  };
}

function makeAnalysis(title: string, maxRiskScore: number): AnalysisResult {
  return {
    engine_version: "0.1.0",
    document_title: title,
    summary: { heuristic_threats_generated: 15, max_risk_score: maxRiskScore },
    structural_findings: [],
    trust_boundary_findings: [],
    heuristic_threats: [],
  } as unknown as AnalysisResult;
}

/** Mirrors the two consumers so a test can drive both contexts at once. */
function useBoth() {
  return { session: useSession(), history: useAnalysisHistory() };
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});
afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe("AnalysisHistoryProvider appendSnapshot", () => {
  it("records the analysis produced by the run that triggered the snapshot", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));

    // Exactly what AnalysisPage.run() does: both calls in one commit.
    const fresh = makeAnalysis("Payments Gateway", 15);
    act(() => {
      result.current.session.setAnalysis(fresh);
      result.current.history.appendSnapshot("analysis", fresh);
    });

    const [entry] = result.current.history.entries;
    expect(entry.analysis?.document_title).toBe("Payments Gateway");
  });

  it("records the max risk score of that same run", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));

    const fresh = makeAnalysis("Payments Gateway", 15);
    act(() => {
      result.current.session.setAnalysis(fresh);
      result.current.history.appendSnapshot("analysis", fresh);
    });

    expect(result.current.history.entries[0].maxScore).toBe(15);
  });

  it("persists the analysis to storage, not just to the in-memory entry", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));

    const fresh = makeAnalysis("Payments Gateway", 15);
    act(() => {
      result.current.session.setAnalysis(fresh);
      result.current.history.appendSnapshot("analysis", fresh);
    });

    expect(loadHistory()[0].analysis).not.toBeNull();
  });

  it("does not lag one run behind across consecutive runs", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));

    const first = makeAnalysis("Payments Gateway", 15);
    act(() => {
      result.current.session.setAnalysis(first);
      result.current.history.appendSnapshot("analysis", first);
    });
    const second = makeAnalysis("Payments Gateway", 20);
    act(() => {
      result.current.session.setAnalysis(second);
      result.current.history.appendSnapshot("analysis", second);
    });

    expect(result.current.history.entries.map((e) => e.maxScore)).toEqual([20, 15]);
  });

  it("records the new analysis even when the document was edited between runs", () => {
    // Editing the document clears the session analysis, so the closure value is
    // null again — the null snapshot was never limited to the first run.
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    const first = makeAnalysis("Payments Gateway", 15);
    act(() => {
      result.current.session.setAnalysis(first);
      result.current.history.appendSnapshot("analysis", first);
    });

    act(() => result.current.session.setDocument(makeDoc("Payments Gateway", "cache")));
    const second = makeAnalysis("Payments Gateway", 20);
    act(() => {
      result.current.session.setAnalysis(second);
      result.current.history.appendSnapshot("analysis", second);
    });

    expect(result.current.history.entries[0].maxScore).toBe(20);
  });

  it("restoring an analysis snapshot puts that analysis back in the session", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    const fresh = makeAnalysis("Payments Gateway", 15);
    act(() => {
      result.current.session.setAnalysis(fresh);
      result.current.history.appendSnapshot("analysis", fresh);
    });

    const id = result.current.history.entries[0].id;
    act(() => result.current.history.restore(id));

    expect(result.current.session.analysis?.document_title).toBe("Payments Gateway");
  });

  it("falls back to the session analysis when the caller passes none", () => {
    // ExportPage snapshots the state already on screen and has nothing fresher
    // to hand over.
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.session.setAnalysis(makeAnalysis("Payments Gateway", 15)));

    act(() => result.current.history.appendSnapshot("export"));

    expect(result.current.history.entries[0].maxScore).toBe(15);
  });

  it("stores no entry when there is no document", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });

    act(() => result.current.history.appendSnapshot("analysis", makeAnalysis("Ghost", 1)));

    expect(result.current.history.entries).toEqual([]);
  });

  it("removes the entry the user deletes", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));

    const id = result.current.history.entries[0].id;
    act(() => result.current.history.remove(id));

    expect(result.current.history.entries).toEqual([]);
  });

  it("restore is a no-op for an id that is not in storage", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));

    act(() => result.current.history.restore("h_missing"));

    expect(result.current.session.document?.metadata.title).toBe("Payments Gateway");
  });

  it("refresh re-reads entries written by another tab", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));
    localStorage.setItem("otm.analysis.history", "[]");

    act(() => result.current.history.refresh());

    expect(result.current.history.entries).toEqual([]);
  });

  it("throws a named error when used outside its provider", () => {
    expect(() => renderHook(() => useAnalysisHistory())).toThrow(
      /outside AnalysisHistoryProvider/,
    );
  });
});
