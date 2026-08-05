/**
 * Routing contract.
 *
 * Until now the web suite had 68 tests and not one of them touched the router. That gap was
 * found the hard way: the `react-router-dom` -> `react-router` v8 migration changed the
 * import in 15 files and the unit suite stayed green throughout, proving nothing. The only
 * safety net was Playwright, which does not run on every change.
 *
 * These tests exercise the route table itself: every declared path resolves to its own URL,
 * and an unknown one redirects home instead of leaving the user on a blank screen.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import { APP_ROUTES, AppRoutes } from "./App";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";

/** Reports the URL the router settled on, which is the thing under test. */
function LocationProbe() {
  const { pathname } = useLocation();
  return <span data-testid="pathname">{pathname}</span>;
}

function renderAt(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <ToastProvider>
          <AppRoutes />
          <LocationProbe />
        </ToastProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

async function settledPath(): Promise<string> {
  // Pages are lazy, so the first paint is the Suspense fallback; wait for the probe.
  await waitFor(() => expect(screen.getByTestId("pathname")).toBeInTheDocument());
  return screen.getByTestId("pathname").textContent ?? "";
}

describe("route table", () => {
  it.each(APP_ROUTES)("%s resolves to itself and is not swallowed by the catch-all", async (path) => {
    renderAt(path);
    expect(await settledPath()).toBe(path);
  });

  it.each([
    "/does-not-exist",
    "/wizard/extra/segments",
    "/ANALYSIS",
    "/%C3%A7%C3%A3o",
  ])("unknown path %s redirects home rather than showing nothing", async (path) => {
    renderAt(path);
    // `replace` is deliberate: Back must not bounce the user into the dead URL again.
    await waitFor(async () => expect(await settledPath()).toBe("/"));
  });

  it("declares no duplicate paths", () => {
    expect(new Set(APP_ROUTES).size).toBe(APP_ROUTES.length);
  });

  it("keeps the home route, which every unknown URL falls back to", () => {
    expect(APP_ROUTES).toContain("/");
  });
});
