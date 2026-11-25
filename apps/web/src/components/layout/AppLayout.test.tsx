/**
 * "New model" sits in the header of every page and used to wipe the session document on a
 * single click: no confirmation, no undo, and — for a model that had never been analysed —
 * no History snapshot to fall back on either. The home page states the draft lives only in
 * this browser session, so that click destroyed the only copy of the user's work. The
 * History page already asks before replacing the session; the header now does too.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppLayout } from "./AppLayout";
import { SessionProvider } from "../../context/SessionContext";
import { ThemeProvider } from "../../context/ThemeContext";
import i18n from "../../i18n/i18n";
import type { OtmDocument } from "../../types/document";

const DOC_KEY = "otm.web.document";

function seedDocument(): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title: "Two hours of modelling", tags: [] },
    components: [{ id: "a1", name: "A1", kind: "process" }],
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
    <MemoryRouter initialEntries={["/wizard"]}>
      <ThemeProvider>
        <SessionProvider>{children}</SessionProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  sessionStorage.setItem(DOC_KEY, JSON.stringify(seedDocument()));
});

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe('AppLayout "New model"', () => {
  it("asks before discarding the session model", async () => {
    const confirmSpy = vi.spyOn(globalThis, "confirm").mockReturnValue(false);
    render(<AppLayout />, { wrapper: Providers });

    await userEvent.click(screen.getByRole("button", { name: i18n.t("nav.newModel") }));

    expect(confirmSpy).toHaveBeenCalledWith(i18n.t("nav.confirmNewModel"));
  });

  it("keeps the model when the user cancels", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(false);
    render(<AppLayout />, { wrapper: Providers });

    await userEvent.click(screen.getByRole("button", { name: i18n.t("nav.newModel") }));

    expect(sessionStorage.getItem(DOC_KEY)).not.toBeNull();
  });

  it("discards the model once the user confirms", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    render(<AppLayout />, { wrapper: Providers });

    await userEvent.click(screen.getByRole("button", { name: i18n.t("nav.newModel") }));

    expect(sessionStorage.getItem(DOC_KEY)).toBeNull();
  });

  it("offers no discard control at all when there is no model to lose", () => {
    sessionStorage.clear();
    render(<AppLayout />, { wrapper: Providers });

    expect(screen.queryByRole("button", { name: i18n.t("nav.newModel") })).toBeNull();
  });
});

/**
 * WCAG 2.4.1 Bypass Blocks, Level A.
 *
 * Tabbing into any route cost twenty stops before the first control on the page: ten in the
 * header (logo, six nav links, two selects, "New model"), six in the WorkflowGuide
 * breadcrumb — which repeats six of the header's own destinations — and four in the wizard
 * stepper. That block is identical on every page, and there was no way past it: no skip
 * link existed and `<main>` carried neither an `id` nor a `tabindex`, so there was nothing
 * to aim one at.
 *
 * The count is asserted rather than the link's presence, because a skip link that points at
 * a target the browser will not focus is decoration.
 */
describe("AppLayout bypass block", () => {
  /** Every element the browser would stop on, in order, inside the rendered layout. */
  function tabStops(container: HTMLElement): HTMLElement[] {
    const candidates = container.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    return [...candidates].filter((el) => !el.hasAttribute("disabled"));
  }

  it("puts the skip link first, before the whole navigation block", () => {
    const { container } = render(<AppLayout />, { wrapper: Providers });

    expect(tabStops(container)[0]).toHaveTextContent(i18n.t("layout.skipToContent"));
  });

  it("aims it at a target that exists", () => {
    const { container } = render(<AppLayout />, { wrapper: Providers });
    const skip = tabStops(container)[0] as HTMLAnchorElement;

    expect(container.querySelector(skip.getAttribute("href") ?? "")).not.toBeNull();
  });

  it("aims it at the main landmark specifically, not at some other element", () => {
    const { container } = render(<AppLayout />, { wrapper: Providers });

    expect(container.querySelector("#main")?.tagName).toBe("MAIN");
  });

  it("makes that target focusable, so the jump actually moves focus", () => {
    const { container } = render(<AppLayout />, { wrapper: Providers });

    expect(container.querySelector("main")).toHaveAttribute("tabindex", "-1");
  });

  it("keeps the target out of the ordinary tab sequence", () => {
    const { container } = render(<AppLayout />, { wrapper: Providers });

    expect(tabStops(container).some((el) => el.tagName === "MAIN")).toBe(false);
  });

  it("hides the link until it takes focus, so sighted mouse users never see it", () => {
    const { container } = render(<AppLayout />, { wrapper: Providers });

    expect(tabStops(container)[0]).toHaveClass("sr-only");
  });

  it("reaches the skip link on the very first Tab", async () => {
    render(<AppLayout />, { wrapper: Providers });

    await userEvent.tab();

    expect(document.activeElement).toHaveTextContent(i18n.t("layout.skipToContent"));
  });
});
