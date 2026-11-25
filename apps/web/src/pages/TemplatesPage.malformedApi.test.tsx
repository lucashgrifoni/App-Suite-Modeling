/**
 * A 200 that is not this API took the Templates page down into the global error boundary.
 *
 * Deployment shapes that produce it: a static host with SPA fallback serving `index.html`
 * for `/api/v1/templates`, a dev proxy pointed at the wrong port, a gateway answering with
 * a captive-portal page, or an upstream returning a zero-byte body. The page called `.map`
 * on whatever came back, so the user got "Something went wrong in the UI / items.map is not
 * a function" — minified to "S.map is not a function" in a production build — and lost the
 * page's own filters and retry affordance, on one of the three advertised entry points.
 *
 * Unlike the sibling suite, this file does NOT mock `../api/otmApi`: the defect lived in the
 * real client, so the whole path from `fetch` to the rendered page is exercised.
 */
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TemplatesPage } from "./TemplatesPage";
import { ErrorBoundary } from "../components/error/ErrorBoundary";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";

function respondWith(body: string, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    statusText: `HTTP ${status}`,
    text: () => Promise.resolve(body),
  } as Response);
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/templates"]}>
      <ToastProvider>
        <SessionProvider>
          <ErrorBoundary>{children}</ErrorBoundary>
        </SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe.each([
  ["an SPA-fallback HTML page", "<!doctype html><title>App Suite Modeling</title>"],
  ["a zero-byte body", ""],
  ["truncated JSON", '{"items": [{"id": "a", "titl'],
])("Templates page against a 200 carrying %s", (_label, body) => {
  it("shows the app's own guidance instead of a runtime error message", async () => {
    vi.stubGlobal("fetch", respondWith(body));

    render(<TemplatesPage />, { wrapper: Providers });

    const alert = await screen.findByRole("alert", {}, { timeout: 3000 });
    expect(alert).toHaveTextContent(/Could not reach the API/);
  });

  it("keeps the page usable rather than replacing it with the error boundary", async () => {
    vi.stubGlobal("fetch", respondWith(body));

    render(<TemplatesPage />, { wrapper: Providers });

    await screen.findByRole("alert", {}, { timeout: 3000 });
    expect(screen.queryByText(/Something went wrong in the UI/)).toBeNull();
    // The filters are the page's recovery affordance; the boundary fallback destroys them.
    expect(document.querySelector("#tpl-search")).not.toBeNull();
  });
});
