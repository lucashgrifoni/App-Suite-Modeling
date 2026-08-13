/**
 * Every history entry carried a pre-rendered `summaryLine` built in `buildEntry` as
 * `` `${title} · L×I máx. ${score}` `` — a Portuguese string assembled outside i18n and then
 * frozen into localStorage. With the UI in English (the default) it printed "L×I máx. —"
 * directly under the page's own English "Max L×I: —", and no locale change could ever fix it
 * because the text was written at snapshot time, not at render time.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HistoryPage } from "./HistoryPage";
import { downloadPdfBlob, generateReportPdfBlob } from "../lib/generateReportPdf";
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

/**
 * "PDF from this snapshot" had no in-flight state at all: the label never changed, the
 * button never disabled, and client-side jsPDF rendering takes seconds on a real model. The
 * natural response to a control that appears to do nothing is to click it again — three
 * clicks ~200 ms apart produced three full renders and three identically named files in the
 * Downloads folder, with no feedback at any point. Every PDF button on the export page
 * already gates on its loading flag and swaps its label.
 */
describe("HistoryPage snapshot PDF", () => {
  // `restoreMocks` only resets spies, and these two come from a module factory, so their
  // call history would otherwise carry over between tests and make the counts meaningless.
  beforeEach(() => {
    vi.mocked(generateReportPdfBlob).mockReset();
    vi.mocked(downloadPdfBlob).mockReset();
  });

  /** A render that never settles, i.e. what the user is looking at while it works. */
  function pendingRender() {
    const gen = vi.mocked(generateReportPdfBlob);
    gen.mockReturnValue(new Promise<Blob>(() => {}));
    return gen;
  }

  function pdfButton() {
    return screen.getByRole("button", { name: /PDF/i });
  }

  it("tells the user the render started", async () => {
    pendingRender();
    render(<HistoryPage />, { wrapper: Providers });

    await userEvent.click(pdfButton());

    expect(screen.getByText(i18n.t("history.pdfSnapshotLoading"))).toBeInTheDocument();
  });

  it("disables the button while it works", async () => {
    pendingRender();
    render(<HistoryPage />, { wrapper: Providers });

    await userEvent.click(pdfButton());

    expect(pdfButton()).toBeDisabled();
  });

  it("does not start a second render when the user clicks again", async () => {
    const gen = pendingRender();
    render(<HistoryPage />, { wrapper: Providers });

    const user = userEvent.setup();
    await user.click(pdfButton());
    await user.click(pdfButton());
    await user.click(pdfButton());

    expect(gen).toHaveBeenCalledTimes(1);
  });

  it("produces exactly one file for those three clicks", async () => {
    pendingRender();
    render(<HistoryPage />, { wrapper: Providers });

    const user = userEvent.setup();
    await user.click(pdfButton());
    await user.click(pdfButton());
    await user.click(pdfButton());

    expect(vi.mocked(downloadPdfBlob)).not.toHaveBeenCalled();
  });

  it("downloads the file and re-enables the button once the render finishes", async () => {
    vi.mocked(generateReportPdfBlob).mockResolvedValue(new Blob(["%PDF-1.4"]));
    render(<HistoryPage />, { wrapper: Providers });

    await userEvent.click(pdfButton());

    await waitFor(() => expect(vi.mocked(downloadPdfBlob)).toHaveBeenCalledTimes(1));
    expect(pdfButton()).toBeEnabled();
  });

  /** A failed render must not leave the control disabled for the rest of the session. */
  it("re-enables the button when the render fails", async () => {
    vi.mocked(generateReportPdfBlob).mockRejectedValue(new Error("jsPDF exploded"));
    render(<HistoryPage />, { wrapper: Providers });

    await userEvent.click(pdfButton());

    await waitFor(() => expect(pdfButton()).toBeEnabled());
  });

  it("shows the ordinary label again after a successful render", async () => {
    vi.mocked(generateReportPdfBlob).mockResolvedValue(new Blob(["%PDF-1.4"]));
    render(<HistoryPage />, { wrapper: Providers });

    await userEvent.click(pdfButton());

    await waitFor(() =>
      expect(screen.getByText(i18n.t("history.pdfSnapshot"))).toBeInTheDocument(),
    );
  });
});
