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
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { SessionProvider, useSession } from "./SessionContext";
import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";

const ANALYSIS_KEY = "otm.web.analysis";

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

  it("does not resurrect a stale analysis from sessionStorage on reload", () => {
    sessionStorage.setItem(ANALYSIS_KEY, JSON.stringify(makeAnalysis("Discarded model")));
    // No paired document fingerprint was stored, so the analysis is unattributable.
    sessionStorage.setItem("otm.web.document", JSON.stringify(makeDoc("Different model")));

    const { result } = renderHook(() => useSession(), { wrapper });

    expect(result.current.document?.metadata.title).toBe("Different model");
    expect(result.current.analysis).toBeNull();
  });
});
