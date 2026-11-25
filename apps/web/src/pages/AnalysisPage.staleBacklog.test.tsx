/**
 * The remediation backlog outlived the analysis it was computed from.
 *
 * `fetchRemediationBacklog({ document, analysis })` derives the backlog from ONE analysis run.
 * Running the analysis again replaced `analysis` and left `backlog` untouched, so the metrics,
 * the cockpit and the threat list switched to the new run while the backlog card kept rendering
 * the previous one — its executive summary, its top-5 actions, its quick wins — with nothing on
 * screen saying the two came from different runs.
 *
 * The backlog is the part a person acts on. Reading it beside metrics from another run is the
 * kind of wrong that looks right.
 *
 * `recommendation` is deliberately NOT cleared alongside it: `recommendMethodology(doc)` depends
 * on the document, not on the analysis, so a new run does not invalidate it. The claim that both
 * were stale was only half true.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisPage } from "./AnalysisPage";
import { AnalysisHistoryProvider } from "../context/AnalysisHistoryContext";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import type { OtmDocument } from "../types/document";

const DOC = {
  model: { schema_version: "1.0.0", system_type: "web_application", industry_sector: "generic", methodology: "stride" },
  metadata: { title: "Portal admin", tags: [] },
  components: [{ id: "admin", name: "Administrador", kind: "external_entity" }],
  data_flows: [],
  trust_boundaries: [],
  assets: [],
  threats: [],
  mitigations: [],
  evidence_suggestions: [],
} as unknown as OtmDocument;

const SUMMARY_RUN_A = "Resumo executivo da PRIMEIRA execucao";

function analysis(methodology: string) {
  return {
    schema_version: "1.0.0",
    engine_version: "7.9.0",
    methodology,
    document_title: "Portal admin",
    summary: { total_threats: 1, max_risk_score: 9, by_severity: {}, by_category: {} },
    heuristic_threats: [],
    structural_findings: [],
    trust_boundary_findings: [],
    explanations: [],
  };
}

const BACKLOG = {
  schema_version: "1.0.0",
  document_title: "Portal admin",
  methodology: "stride",
  executive_summary: SUMMARY_RUN_A,
  synergy_notes: [],
  items: [],
  by_root_cause: {},
  quick_win_ids: [],
  foundational_ids: [],
  high_impact_ids: [],
  top_5_action_ids: [],
};

function jsonOnce(body: unknown) {
  return { ok: true, status: 200, statusText: "OK", text: () => Promise.resolve(JSON.stringify(body)) } as Response;
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/analysis"]}>
      <ToastProvider>
        <SessionProvider>
          <AnalysisHistoryProvider>{children}</AnalysisHistoryProvider>
        </SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  sessionStorage.setItem("otm.web.document", JSON.stringify(DOC));
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) =>
      Promise.resolve(
        String(url).includes("/remediation/backlog") ? jsonOnce(BACKLOG) : jsonOnce(analysis("stride")),
      ),
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function runAnalysis() {
  await userEvent.setup().click(screen.getByRole("button", { name: /Run analysis/i }));
}

describe("AnalysisPage after a second analysis run", () => {
  it("shows the backlog of the run it was generated from", async () => {
    render(<AnalysisPage />, { wrapper: Providers });
    await runAnalysis();
    await waitFor(() => expect(screen.getByRole("button", { name: /backlog/i })).toBeEnabled());
    await userEvent.setup().click(screen.getByRole("button", { name: /backlog/i }));

    expect(await screen.findByText(SUMMARY_RUN_A)).toBeInTheDocument();
  });

  it("drops the previous run's backlog when the analysis is replaced", async () => {
    render(<AnalysisPage />, { wrapper: Providers });
    await runAnalysis();
    await waitFor(() => expect(screen.getByRole("button", { name: /backlog/i })).toBeEnabled());
    await userEvent.setup().click(screen.getByRole("button", { name: /backlog/i }));
    await screen.findByText(SUMMARY_RUN_A);

    await runAnalysis();

    await waitFor(() => expect(screen.queryByText(SUMMARY_RUN_A)).toBeNull());
  });
});
