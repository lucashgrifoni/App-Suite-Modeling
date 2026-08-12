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
