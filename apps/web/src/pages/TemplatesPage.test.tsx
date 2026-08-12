/**
 * The template list refetches on every filter change, and its error state was write-only:
 * the effect called `setError` on failure but never `setError(null)` on success, and never
 * dropped the rows it had already shown. One transient 5xx while typing therefore left a
 * red banner pinned over a working page for the rest of the visit, and during the failed
 * window the user saw the PREVIOUS query's rows under the new search text — a list that
 * looks like a result but is not.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TemplatesPage } from "./TemplatesPage";
import { ApiError } from "../api/client";
import { listTemplates } from "../api/otmApi";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import type { TemplateListItem } from "../types/api";

vi.mock("../api/otmApi", () => ({
  listTemplates: vi.fn(),
  instantiateTemplate: vi.fn(),
}));

const listTemplatesMock = vi.mocked(listTemplates);

function template(id: string): TemplateListItem {
  return {
    id,
    title: `Template ${id}`,
    description: "",
    category: "applications",
    category_label: "Applications",
  };
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/templates"]}>
      <ToastProvider>
        <SessionProvider>{children}</SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

/** Rows are `data-testid="tpl-row-<id>"`; counting them is the list state under test. */
function rowIds(): string[] {
  return screen
    .queryAllByTestId(/^tpl-row-/)
    .map((el) => el.getAttribute("data-testid")?.replace("tpl-row-", "") ?? "");
}

/** By id, not by label: the label reads "Text" in en and "Texto" in pt-BR. */
function searchBox(): HTMLInputElement {
  return document.querySelector<HTMLInputElement>("#tpl-search")!;
}

beforeEach(() => {
  listTemplatesMock.mockReset();
});

describe("TemplatesPage list error handling", () => {
  it("clears the error banner once a later fetch succeeds", async () => {
    const user = userEvent.setup();
    listTemplatesMock
      .mockResolvedValueOnce([template("alpha")])
      .mockRejectedValueOnce(new ApiError("transient failure", 503, null))
      .mockResolvedValueOnce([template("beta")]);

    render(<TemplatesPage />, { wrapper: Providers });
    await waitFor(() => expect(rowIds()).toEqual(["alpha"]));

    // Each keystroke refetches after the 280ms debounce.
    await user.type(searchBox(), "b");
    await screen.findByRole("alert", {}, { timeout: 3000 });
    expect(screen.getByRole("alert")).toHaveTextContent("transient failure");

    await user.type(searchBox(), "e");
    await waitFor(() => expect(rowIds()).toEqual(["beta"]), { timeout: 3000 });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("does not keep showing the previous query's rows while reporting a failure", async () => {
    const user = userEvent.setup();
    listTemplatesMock
      .mockResolvedValueOnce([template("alpha"), template("gamma")])
      .mockRejectedValueOnce(new ApiError("transient failure", 503, null));

    render(<TemplatesPage />, { wrapper: Providers });
    await waitFor(() => expect(rowIds()).toEqual(["alpha", "gamma"]));

    await user.type(searchBox(), "b");
    await screen.findByRole("alert", {}, { timeout: 3000 });

    // Rows that answered a different query must not sit under the new search text as if
    // they were its result — the user can click one believing it matched.
    expect(rowIds()).toEqual([]);
  });
});
