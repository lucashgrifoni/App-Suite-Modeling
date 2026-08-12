/**
 * The revised-model upload on /diff was a bare `<input type="file">` — no id, no label, no
 * aria-label, no title. A screen reader announced an unnamed button on one of only two ways
 * to supply the revised document (WCAG 2.2 SC 4.1.2), while every other file input in the
 * app follows ImportPage's `<Label htmlFor=… className="sr-only">` pattern. The same handler
 * also registered `onload` but no `onerror`, so a read that failed said nothing at all.
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

vi.mock("../api/otmApi", () => ({
  compareThreatModels: vi.fn(),
}));

const compareMock = vi.mocked(compareThreatModels);

const DOC_KEY = "otm.web.document";

/** /diff redirects home without a baseline in the session. */
function seedDocument(): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title: "Diff fixture", tags: [] },
    components: [{ id: "api", name: "Api", kind: "process" }],
    data_flows: [],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  };
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
  sessionStorage.setItem(DOC_KEY, JSON.stringify(seedDocument()));
});

describe("DiffPage revised-model upload", () => {
  it("gives the file input an accessible name", () => {
    render(<DiffPage />, { wrapper: Providers });

    const named = screen.getByLabelText(i18n.t("diff.revisionFileLabel"));
    expect(named).toBe(document.querySelector('input[type="file"]'));
  });

  it("leaves no form control on the page without an accessible name", () => {
    render(<DiffPage />, { wrapper: Providers });

    // Cheap standing guard for the whole class of defect: aria-label -> aria-labelledby ->
    // title -> label[for] -> ancestor <label>, which is the order a screen reader resolves.
    const unnamed = [...document.querySelectorAll("input, select, textarea")].filter((el) => {
      if (el.getAttribute("aria-label")?.trim()) return false;
      if (el.getAttribute("aria-labelledby")?.trim()) return false;
      if (el.getAttribute("title")?.trim()) return false;
      if (el.closest("label")) return false;
      const id = el.getAttribute("id");
      return !(id && document.querySelector(`label[for="${id}"]`)?.textContent?.trim());
    });

    expect(unnamed.map((el) => `${el.tagName}:${el.getAttribute("type") ?? ""}`)).toEqual([]);
  });

  it("reports a failed file read instead of staying silent", async () => {
    const user = userEvent.setup();
    // jsdom cannot make a real read fail; the stub is the only way to reach the branch.
    // `unstubGlobals` in vitest.config restores the real FileReader after this test.
    vi.stubGlobal(
      "FileReader",
      class {
        onload: (() => void) | null = null;
        onerror: (() => void) | null = null;
        result: string | null = null;
        readAsText() {
          queueMicrotask(() => this.onerror?.());
        }
      },
    );

    render(<DiffPage />, { wrapper: Providers });
    const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;

    await user.upload(input, new File(["{}"], "revised.json", { type: "application/json" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(i18n.t("diff.readFail"));
    });
  });
});

const EMPTY_SECTION = { added: [], removed: [], changed: [] };

function comparisonResult(
  overrides: Partial<ThreatModelComparisonResult> = {},
): ThreatModelComparisonResult {
  return {
    summary: {
      headline: "baseline «A» → revision «A»: no structural differences detected.",
      has_structural_changes: false,
      has_analysis_changes: false,
    },
    // The server fills `structural.summary_line` with the very same sentence.
    structural: { summary_line: "baseline «A» → revision «A»: no structural differences detected." },
    aggregate: {
      components: EMPTY_SECTION,
      assets: EMPTY_SECTION,
      data_flows: EMPTY_SECTION,
      trust_boundaries: EMPTY_SECTION,
      threats: EMPTY_SECTION,
      mitigations: EMPTY_SECTION,
    },
    risk_delta: {},
    key_insights: [],
    meta: {},
    ...overrides,
  } as unknown as ThreatModelComparisonResult;
}

/** Fill the revision box and press Compare, resolving with `result`. */
async function compareWith(result: ThreatModelComparisonResult) {
  const user = userEvent.setup();
  compareMock.mockResolvedValueOnce(result);
  render(<DiffPage />, { wrapper: Providers });
  // fireEvent, not user.type: the box wants a whole canonical document, and typing one
  // character at a time through hundreds of JSON characters is pure test latency.
  fireEvent.change(screen.getByLabelText(i18n.t("diff.revisionJson")), {
    target: { value: JSON.stringify(seedDocument()) },
  });
  await user.click(screen.getByRole("button", { name: i18n.t("diff.compare") }));
  await waitFor(() => expect(compareMock).toHaveBeenCalled());
}

describe("DiffPage summary card", () => {
  it("does not print the same sentence twice", async () => {
    // `summary.headline` and `structural.summary_line` are distinct fields that the server
    // usually fills identically, so the card showed one bold line followed by a byte-identical
    // muted one — in the no-change case and the with-change case alike.
    const sentence = "baseline «A» → revision «A»: no structural differences detected.";
    await compareWith(comparisonResult());

    // Paragraphs only: the "Full JSON" <pre> at the bottom legitimately echoes the payload.
    const matches = screen.getAllByText(sentence, { exact: false, selector: "p" });
    expect(matches).toHaveLength(1);
  });

  it("still shows the structural line when it adds something new", async () => {
    await compareWith(
      comparisonResult({
        structural: { summary_line: "3 fields changed at the top level." },
      } as Partial<ThreatModelComparisonResult>),
    );

    expect(screen.getByText("3 fields changed at the top level.")).toBeInTheDocument();
  });
});

describe("DiffPage changes-by-section card", () => {
  it("says there were no changes instead of rendering an empty body", async () => {
    // Every AggregateBlock returns null when its section is untouched, so an identical
    // revision produced a heading with literally nothing under it — indistinguishable from
    // a section that failed to load.
    await compareWith(comparisonResult());

    expect(screen.getByText(i18n.t("diff.noSectionChanges"))).toBeInTheDocument();
  });

  it("lists the sections that did change", async () => {
    await compareWith(
      comparisonResult({
        aggregate: {
          components: { added: ["cache"], removed: [], changed: [] },
          assets: EMPTY_SECTION,
          data_flows: EMPTY_SECTION,
          trust_boundaries: EMPTY_SECTION,
          threats: EMPTY_SECTION,
          mitigations: EMPTY_SECTION,
        },
      } as Partial<ThreatModelComparisonResult>),
    );

    expect(screen.getByText("cache")).toBeInTheDocument();
  });

  it("drops the empty-state line once a section has changes", async () => {
    await compareWith(
      comparisonResult({
        aggregate: {
          components: { added: ["cache"], removed: [], changed: [] },
          assets: EMPTY_SECTION,
          data_flows: EMPTY_SECTION,
          trust_boundaries: EMPTY_SECTION,
          threats: EMPTY_SECTION,
          mitigations: EMPTY_SECTION,
        },
      } as Partial<ThreatModelComparisonResult>),
    );

    expect(screen.queryByText(i18n.t("diff.noSectionChanges"))).toBeNull();
  });
});
