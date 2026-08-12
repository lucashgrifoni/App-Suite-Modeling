/**
 * Every history entry carried a pre-rendered `summaryLine` built in `buildEntry` as
 * `` `${title} · L×I máx. ${score}` `` — a Portuguese string assembled outside i18n and then
 * frozen into localStorage. With the UI in English (the default) it printed "L×I máx. —"
 * directly under the page's own English "Max L×I: —", and no locale change could ever fix it
 * because the text was written at snapshot time, not at render time.
 */

import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HistoryPage } from "./HistoryPage";
import { AnalysisHistoryProvider } from "../context/AnalysisHistoryContext";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { AnalysisHistoryEntry } from "../types/analysisHistory";

// jsPDF pulls a large canvas/font stack that jsdom cannot run and this page never exercises.
vi.mock("../lib/generateReportPdf", () => ({
  generateReportPdfBlob: vi.fn(),
  downloadPdfBlob: vi.fn(),
}));

const HISTORY_KEY = "otm.analysis.history";

function storedEntry(): AnalysisHistoryEntry {
  return {
    id: "h1",
    createdAt: 1_770_000_000_000,
    trigger: "analysis",
    title: "Payments Gateway",
    systemType: "api_backend",
    maxScore: 15,
    document: {
      model: {
        schema_version: "1.0.0",
        system_type: "api_backend",
        industry_sector: "generic",
        methodology: "stride",
      },
      metadata: { title: "Payments Gateway", tags: [] },
      components: [{ id: "api", name: "Api", kind: "process" }],
      data_flows: [],
      trust_boundaries: [],
      assets: [],
      threats: [],
      mitigations: [],
      evidence_suggestions: [],
    },
    analysis: null,
  } as unknown as AnalysisHistoryEntry;
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/history"]}>
      <ToastProvider>
        <SessionProvider>
          <AnalysisHistoryProvider>{children}</AnalysisHistoryProvider>
        </SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  localStorage.setItem(HISTORY_KEY, JSON.stringify([storedEntry()]));
});

afterEach(async () => {
  localStorage.clear();
  await i18n.changeLanguage("en");
});

describe("HistoryPage snapshot summary line", () => {
  it("renders the summary line in English when the UI is English", () => {
    render(<HistoryPage />, { wrapper: Providers });

    expect(screen.getByText("Payments Gateway · max L×I 15")).toBeInTheDocument();
  });

  it("leaves no Portuguese abbreviation on an English page", () => {
    render(<HistoryPage />, { wrapper: Providers });

    expect(document.body.textContent).not.toContain("máx.");
  });

  it("renders the same line in Portuguese once the locale changes", async () => {
    await i18n.changeLanguage("pt-BR");

    render(<HistoryPage />, { wrapper: Providers });

    expect(screen.getByText("Payments Gateway · L×I máx. 15")).toBeInTheDocument();
  });

  it("shows a dash for an entry with no score", () => {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify([{ ...storedEntry(), maxScore: null }]),
    );

    render(<HistoryPage />, { wrapper: Providers });

    expect(screen.getByText("Payments Gateway · max L×I —")).toBeInTheDocument();
  });

  it("reports an attached analysis in the snapshot summary", () => {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify([
        {
          ...storedEntry(),
          analysis: { summary: { max_risk_score: 15 }, heuristic_threats: [{ id: "t1" }] },
        },
      ]),
    );

    render(<HistoryPage />, { wrapper: Providers });

    expect(screen.getByText(/"analysis_attached": true/)).toBeInTheDocument();
  });
});
