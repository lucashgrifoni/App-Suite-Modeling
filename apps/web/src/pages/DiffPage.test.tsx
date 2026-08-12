/**
 * The revised-model upload on /diff was a bare `<input type="file">` — no id, no label, no
 * aria-label, no title. A screen reader announced an unnamed button on one of only two ways
 * to supply the revised document (WCAG 2.2 SC 4.1.2), while every other file input in the
 * app follows ImportPage's `<Label htmlFor=… className="sr-only">` pattern. The same handler
 * also registered `onload` but no `onerror`, so a read that failed said nothing at all.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DiffPage } from "./DiffPage";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { OtmDocument } from "../types/document";

vi.mock("../api/otmApi", () => ({
  compareThreatModels: vi.fn(),
}));

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
