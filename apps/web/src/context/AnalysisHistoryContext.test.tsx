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
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisHistoryProvider, useAnalysisHistory } from "./AnalysisHistoryContext";
import { SessionProvider, useSession } from "./SessionContext";
import { loadHistory } from "../utils/analysisHistoryStorage";
import type { AnalysisHistoryEntry } from "../types/analysisHistory";
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

const HISTORY_KEY = "otm.analysis.history";

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

/**
 * History is localStorage, which every tab on the origin shares, but the provider read it
 * once at mount and never again. A second tab left open on /history therefore kept rendering
 * the list as it stood when that tab was opened — with no hint it was stale — and its Remove
 * button acted on a list nobody was looking at, so unrelated entries appeared on screen as
 * the visible result of a delete.
 */
describe("AnalysisHistoryProvider cross-tab synchronisation", () => {
  function entryFromAnotherTab(id: string): AnalysisHistoryEntry {
    return {
      id,
      createdAt: 1_770_000_000_000,
      trigger: "analysis",
      title: "Written elsewhere",
      systemType: "api_backend",
      maxScore: 9,
      document: makeDoc("Written elsewhere"),
      analysis: null,
    };
  }

  /** What a write in another tab looks like to this one. */
  function simulateOtherTabWrite(entries: AnalysisHistoryEntry[]) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
    globalThis.dispatchEvent(new StorageEvent("storage", { key: HISTORY_KEY }));
  }

  it("shows the snapshots another tab added", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));

    act(() => simulateOtherTabWrite([entryFromAnotherTab("t2-a"), entryFromAnotherTab("t2-b")]));

    expect(result.current.history.entries.map((e) => e.id)).toEqual(["t2-a", "t2-b"]);
  });

  it("reacts to another tab clearing the whole store", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));

    act(() => {
      localStorage.clear();
      globalThis.dispatchEvent(new StorageEvent("storage", { key: null }));
    });

    expect(result.current.history.entries).toEqual([]);
  });

  it("ignores writes to keys that are not the history list", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));
    const before = result.current.history.entries;

    act(() => {
      globalThis.dispatchEvent(new StorageEvent("storage", { key: "otm.web.locale" }));
    });

    expect(result.current.history.entries).toBe(before);
  });

  it("catches up when the tab comes back to the foreground", () => {
    // A browser may freeze a background document, which then receives no `storage` event
    // for the whole time it was away — the tab in the report had been open for minutes.
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));
    localStorage.setItem(HISTORY_KEY, JSON.stringify([entryFromAnotherTab("while-hidden")]));

    act(() => {
      globalThis.document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(result.current.history.entries.map((e) => e.id)).toEqual(["while-hidden"]);
  });

  it("does not re-read while the tab is still hidden", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));
    const before = result.current.history.entries;
    vi.spyOn(globalThis.document, "visibilityState", "get").mockReturnValue("hidden");

    act(() => {
      globalThis.document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(result.current.history.entries).toBe(before);
  });

  it("stops listening once unmounted", () => {
    const { result, unmount } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    act(() => result.current.history.appendSnapshot("export"));
    unmount();

    expect(() => simulateOtherTabWrite([entryFromAnotherTab("after-unmount")])).not.toThrow();
  });
});

/**
 * When the origin quota is exhausted the snapshot cannot be stored at all, and the caller
 * has to know: it is about to announce success for work that will not appear in History.
 */
describe("AnalysisHistoryProvider quota reporting", () => {
  it("reports the storage failure to the caller", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      const err = new Error("The quota has been exceeded.");
      err.name = "QuotaExceededError";
      throw err;
    });

    let outcome: string | undefined;
    act(() => {
      outcome = result.current.history.appendSnapshot("export");
    });

    expect(outcome).toBe("failed");
  });

  it("reports success on an ordinary write", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });
    act(() => result.current.session.setDocument(makeDoc("Payments Gateway")));

    let outcome: string | undefined;
    act(() => {
      outcome = result.current.history.appendSnapshot("export");
    });

    expect(outcome).toBe("ok");
  });

  it("does not claim a storage failure when there was nothing to snapshot", () => {
    const { result } = renderHook(() => useBoth(), { wrapper });

    let outcome: string | undefined;
    act(() => {
      outcome = result.current.history.appendSnapshot("analysis", makeAnalysis("Ghost", 1));
    });

    expect(outcome).toBe("ok");
  });
});
