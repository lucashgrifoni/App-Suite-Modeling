/**
 * The "Include analysis" checkbox was doubling as a display filter.
 *
 * It describes the NEXT request: `compareThreatModels(..., { runAnalysis })` decides whether the
 * server computes the analysis at all. Measured against the real endpoint, a comparison run with
 * `run_analysis: false` comes back with `analysis_max_score_delta: null` and empty
 * `heuristic_*_ids` — so the RESULT already says whether it carries analysis data, and the
 * checkbox adds nothing to that question.
 *
 * The panel gated on the live checkbox anyway. Unticking it after a comparison made the "Max L×I"
 * block and the whole risk-delta card vanish, with no second request, for a `result` that had not
 * changed — while the "Full JSON" card on the same page went on printing the very numbers that
 * had just disappeared.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DiffPage } from "./DiffPage";
import { compareThreatModels } from "../api/otmApi";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { ThreatModelComparisonResult } from "../types/api";
import type { OtmDocument } from "../types/document";

vi.mock("../api/otmApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/otmApi")>()),
  compareThreatModels: vi.fn(),
}));

const compareMock = vi.mocked(compareThreatModels);
const EMPTY = { added: [], removed: [], changed: [] };

function seedDocument(): OtmDocument {
  return {
    model: { schema_version: "1.0.0" },
    metadata: { title: "A", tags: [] },
    components: [],
    data_flows: [],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  } as unknown as OtmDocument;
}

function withAnalysis(): ThreatModelComparisonResult {
  return {
    summary: { headline: "baseline «A» → revision «A»", has_structural_changes: false, has_analysis_changes: true },
    structural: { summary_line: "" },
    aggregate: {
      components: EMPTY, assets: EMPTY, data_flows: EMPTY,
      trust_boundaries: EMPTY, threats: EMPTY, mitigations: EMPTY,
    },
    risk_delta: {
      analysis_max_score_delta: 6,
      analysis_max_score_baseline: 9,
      analysis_max_score_revised: 15,
      heuristic_increased_ids: ["t1"],
      heuristic_decreased_ids: [],
    },
    key_insights: [],
    meta: {},
  } as unknown as ThreatModelComparisonResult;
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/diff"]}>
      <ToastProvider>
        <SessionProvider>{children}</SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  compareMock.mockReset();
  sessionStorage.setItem("otm.web.document", JSON.stringify(seedDocument()));
});

async function compareIncludingAnalysis() {
  const user = userEvent.setup();
  compareMock.mockResolvedValueOnce(withAnalysis());
  render(<DiffPage />, { wrapper: Providers });
  await user.click(screen.getByLabelText(i18n.t("diff.includeAnalysis")));
  fireEvent.change(screen.getByLabelText(i18n.t("diff.revisionJson")), {
    target: { value: JSON.stringify(seedDocument()) },
  });
  await user.click(screen.getByRole("button", { name: i18n.t("diff.compare") }));
  await waitFor(() => expect(compareMock).toHaveBeenCalledTimes(1));
  return user;
}

describe("DiffPage after unticking Include analysis", () => {
  it("shows the risk delta the comparison returned", async () => {
    await compareIncludingAnalysis();

    // Os dois portões separados: `maxRev` no cartão de resumo, `hasDelta` no cartão de deltas.
    // A primeira versão deste teste só afirmava o "15" e não distinguia os dois — matar
    // `hasDelta` deixava-a verde. Apanhado por mutação.
    expect(await screen.findByText("15")).toBeInTheDocument();
    expect(screen.getByText(i18n.t("diff.riskDeltas"))).toBeInTheDocument();
  });

  it("keeps showing it, because the result did not change", async () => {
    const user = await compareIncludingAnalysis();
    await screen.findByText("15");

    await user.click(screen.getByRole("button", { name: i18n.t("work.comparisonInputs") }));
    await user.click(screen.getByLabelText(i18n.t("diff.includeAnalysis")));

    expect(compareMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText(i18n.t("diff.riskDeltas"))).toBeInTheDocument();
  });

  it("still sends the checkbox state on the NEXT comparison", async () => {
    const user = await compareIncludingAnalysis();
    await user.click(screen.getByRole("button", { name: i18n.t("work.comparisonInputs") }));
    await user.click(screen.getByLabelText(i18n.t("diff.includeAnalysis")));

    compareMock.mockResolvedValueOnce(withAnalysis());
    await user.click(screen.getByRole("button", { name: i18n.t("diff.compare") }));

    await waitFor(() => expect(compareMock).toHaveBeenCalledTimes(2));
    expect(compareMock.mock.calls[1]?.[2]).toMatchObject({ runAnalysis: false });
  });
});
