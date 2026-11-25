/**
 * A cached analysis must never be shown next to a document it was not computed from.
 *
 * `setDocumentValue` used to clear the analysis only when the new document was `null`.
 * Every producer of a *new* model goes through the same setter — HomePage "create new
 * model", TemplatesPage instantiate, ImportPage — so starting a second model in the same
 * tab silently carried the first model's threat list, risk scores and framework mappings
 * into the second model's analysis screen, its exports, its premium report and its history
 * snapshot. This is an evidence tool; the artifacts it emits are what an auditor reads.
 */

import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionProvider, useSession } from "./SessionContext";
import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";

const ANALYSIS_KEY = "otm.web.analysis";
const ANALYSIS_DOC_KEY = "otm.web.analysis.doc";

function wrapper({ children }: Readonly<{ children: ReactNode }>) {
  return <SessionProvider>{children}</SessionProvider>;
}

function makeDoc(title: string, componentId?: string): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
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

function makeAnalysis(title: string): AnalysisResult {
  return {
    engine_version: "0.1.0",
    document_title: title,
    summary: { heuristic_threats_generated: 32 },
    structural_findings: [],
    trust_boundary_findings: [],
    heuristic_threats: [],
  } as unknown as AnalysisResult;
}

beforeEach(() => sessionStorage.clear());
afterEach(() => sessionStorage.clear());

describe("SessionProvider analysis/document pairing", () => {
  it("exposes an analysis computed from the current document", () => {
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));

    expect(result.current.analysis?.document_title).toBe("Model A");
  });

  it("hides the analysis once a different document replaces it", () => {
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.setDocument(makeDoc("Novo threat model")));

    expect(result.current.analysis).toBeNull();
  });

  it("hides the analysis after the document is edited", () => {
    // Same defect, smaller delta: exporting an edited model with the pre-edit
    // engine output is still a mismatched artifact.
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.setDocument(makeDoc("Model A", "new_component")));

    expect(result.current.analysis).toBeNull();
  });

  it("keeps the analysis when the same document is re-set", () => {
    // The wizard calls setDocument on every keystroke; re-normalising an
    // unchanged document must not throw the analysis away.
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.setDocument(makeDoc("Model A")));

    expect(result.current.analysis?.document_title).toBe("Model A");
  });

  it("clears the analysis and its storage when the document is cleared", () => {
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.setDocument(null));

    expect(result.current.analysis).toBeNull();
    expect(sessionStorage.getItem(ANALYSIS_KEY)).toBeNull();
  });

  it("restores a document and its own analysis together", () => {
    // The one legitimate caller that sets both: AnalysisHistoryContext.restore.
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.setDocument(makeDoc("Model B")));
    expect(result.current.analysis).toBeNull();

    act(() => {
      result.current.setDocument(makeDoc("Model A"));
      result.current.setAnalysis(makeAnalysis("Model A"));
    });

    expect(result.current.analysis?.document_title).toBe("Model A");
  });

  it("reset clears both document and analysis", () => {
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.reset());

    expect(result.current.document).toBeNull();
    expect(result.current.analysis).toBeNull();
  });

  it("keeps the analysis usable on this page load even when storage refuses it", () => {
    // The write failing is a caching problem, not an analysis problem: the result the
    // engine just returned must still render, or the fix for the reload case would have
    // created the opposite defect (refusing a legitimate, correctly-paired analysis).
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    vi.spyOn(Storage.prototype, "setItem").mockImplementation((key: string) => {
      if (key === ANALYSIS_KEY) throw new DOMException("quota", "QuotaExceededError");
    });
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));

    expect(result.current.analysis?.document_title).toBe("Model A");
  });

  it("does not stamp the new document's fingerprint on the previous model's cached analysis", () => {
    // The quota failure that made this a correctness bug: a large model's analysis is
    // refused by the browser while the 8-char fingerprint always fits, so storage kept
    // "Model A"'s threat list stamped with "Model B"'s fingerprint and the pairing guard
    // accepted the pair after a reload.
    const { result, unmount } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    expect(sessionStorage.getItem(ANALYSIS_KEY)).not.toBeNull();

    const realSetItem = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (
      this: Storage,
      key: string,
      value: string,
    ) {
      if (key === ANALYSIS_KEY) throw new DOMException("quota", "QuotaExceededError");
      realSetItem.call(this, key, value);
    });
    act(() => result.current.setDocument(makeDoc("Model B")));
    act(() => result.current.setAnalysis(makeAnalysis("Model B")));
    unmount();
    vi.restoreAllMocks();

    // The reload: a fresh provider reading whatever survived in sessionStorage.
    const reloaded = renderHook(() => useSession(), { wrapper });
    expect(reloaded.result.current.document?.metadata.title).toBe("Model B");
    expect(reloaded.result.current.analysis).toBeNull();
    expect(sessionStorage.getItem(ANALYSIS_DOC_KEY)).toBeNull();
  });

  it("drops the cached analysis when only its fingerprint is refused", () => {
    // The mirror image: the analysis lands and the fingerprint does not. An analysis with
    // no fingerprint is unattributable, so it must not stay behind either.
    const { result, unmount } = renderHook(() => useSession(), { wrapper });

    const realSetItem = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (
      this: Storage,
      key: string,
      value: string,
    ) {
      if (key === ANALYSIS_DOC_KEY) throw new DOMException("quota", "QuotaExceededError");
      realSetItem.call(this, key, value);
    });
    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    unmount();
    vi.restoreAllMocks();

    expect(sessionStorage.getItem(ANALYSIS_KEY)).toBeNull();
    const reloaded = renderHook(() => useSession(), { wrapper });
    expect(reloaded.result.current.analysis).toBeNull();
  });

  it("survives a browser that refuses every storage call", () => {
    // Private mode: `removeItem` throws too. The session must still work in memory.
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    const { result } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    act(() => result.current.reset());

    expect(result.current.document).toBeNull();
    expect(result.current.analysis).toBeNull();
  });

  it("restores a correctly paired analysis on reload", () => {
    // Control for the two quota tests: with storage working, the cache still works.
    const { result, unmount } = renderHook(() => useSession(), { wrapper });

    act(() => result.current.setDocument(makeDoc("Model A")));
    act(() => result.current.setAnalysis(makeAnalysis("Model A")));
    unmount();

    const reloaded = renderHook(() => useSession(), { wrapper });
    expect(reloaded.result.current.analysis?.document_title).toBe("Model A");
  });

  it("does not resurrect a stale analysis from sessionStorage on reload", () => {
    sessionStorage.setItem(ANALYSIS_KEY, JSON.stringify(makeAnalysis("Discarded model")));
    // No paired document fingerprint was stored, so the analysis is unattributable.
    sessionStorage.setItem("otm.web.document", JSON.stringify(makeDoc("Different model")));

    const { result } = renderHook(() => useSession(), { wrapper });

    expect(result.current.document?.metadata.title).toBe("Different model");
    expect(result.current.analysis).toBeNull();
  });
});
