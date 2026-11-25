/**
 * Routing contract.
 *
 * Until now the web suite had 68 tests and not one of them touched the router. That gap was
 * found the hard way: the `react-router-dom` -> `react-router` v8 migration changed the
 * import in 15 files and the unit suite stayed green throughout, proving nothing. The only
 * safety net was Playwright, which does not run on every change.
 *
 * The first attempt at closing the gap proved nothing either, and it is worth spelling out
 * so it is not reintroduced. It waited for `LocationProbe`, which is rendered EAGERLY as a
 * sibling of the lazy `<AppRoutes />`: the probe is already in the DOM on `waitFor`'s first
 * synchronous check, so the assertion read `MemoryRouter`'s initial entry before the route
 * had mounted or redirected. Two consequences, both measured: `/wizard` asserted `/wizard`
 * and passed even though an empty session redirects it to `/`, and deleting
 * `<Route path="/history" element={<HistoryPage />} />` from App.tsx left all nine cases
 * green. A pathname read too early is just the string the test itself supplied.
 *
 * So these tests wait on a marker the ROUTE produces — the page's own `<h1>` — and assert
 * WHICH page mounted. The pathname alone can never distinguish a correct route table from
 * an absent one, because the catch-all rewrites the URL but the page identity still differs.
 */
import { render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { APP_ROUTES, AppRoutes } from "./App";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";
import i18n from "./i18n/i18n";
import type { OtmDocument } from "./types/document";

// /templates fetches its list on mount. The subject here is the route table, not the
// network, so the one call that would leave jsdom is stubbed; everything else stays real.
vi.mock("./api/otmApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api/otmApi")>()),
  listTemplates: vi.fn().mockResolvedValue([]),
}));

const DOC_KEY = "otm.web.document";

/**
 * The heading key each route must render, i.e. the proof that the intended page mounted.
 *
 * Compared against `i18n.t(...)` rather than literal text so the test does not depend on
 * which locale jsdom negotiates.
 */
const ROUTE_HEADING_KEY: Record<(typeof APP_ROUTES)[number], string> = {
  "/": "work.overview",
  "/templates": "templates.title",
  "/import": "import.title",
  "/wizard": "wizard.title",
  "/review": "review.title",
  "/analysis": "analysis.title",
  "/export": "export.title",
  "/diff": "diff.title",
  "/history": "history.title",
};

/**
 * Five routes (`/wizard`, `/review`, `/analysis`, `/export`, `/diff`) redirect to `/` when
 * the session holds no document, and `src/test/setup.ts` clears sessionStorage after every
 * test. Without this seed those routes never reach their page and the whole suite would
 * measure the guard instead of the route table.
 */
function seedDocument(): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title: "Routing fixture", tags: [] },
    components: [{ id: "api", name: "Api", kind: "process" }],
    data_flows: [{ id: "f_in", from_component: "api", to_component: "api", name: "In" }],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  };
}

/** Reports the URL the router settled on, which is half of the thing under test. */
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

/**
 * Where the router ended up: the URL AND the page that rendered there.
 *
 * Awaiting the `<h1>` is what makes this honest — it belongs to the lazily loaded page, so
 * it cannot resolve until the route actually mounted. `LocationProbe` is eager and would
 * resolve immediately, which is exactly how the previous version of this file passed while
 * asserting nothing.
 */
async function settled(): Promise<{ path: string; heading: string }> {
  const h1 = await screen.findByRole("heading", { level: 1 });
  return {
    path: screen.getByTestId("pathname").textContent ?? "",
    heading: h1.textContent ?? "",
  };
}

beforeEach(() => {
  sessionStorage.setItem(DOC_KEY, JSON.stringify(seedDocument()));
  // /review renders the reactflow diagram, which constructs a ResizeObserver. jsdom has
  // none, so without this the page throws into AppLayout's ErrorBoundary and the route
  // assertion would be racing a subtree that is being torn down. Stubbed per test because
  // vitest.config sets `unstubGlobals`, which clears stubs after each one.
  if (typeof globalThis.ResizeObserver !== "function") {
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    );
  }
});

describe("route table", () => {
  it.each(APP_ROUTES)("%s mounts its own page and is not swallowed by the catch-all", async (path) => {
    renderAt(path);
    const { path: settledPath, heading } = await settled();
    expect(settledPath).toBe(path);
    expect(heading).toBe(i18n.t(ROUTE_HEADING_KEY[path]));
  });

  it("declares a page marker for every route, so a new route cannot skip this check", () => {
    expect(Object.keys(ROUTE_HEADING_KEY).sort()).toEqual([...APP_ROUTES].sort());
  });

  it("gives every route a distinct marker, otherwise the assertions above are ambiguous", () => {
    const headings = Object.values(ROUTE_HEADING_KEY).map((k) => i18n.t(k));
    expect(new Set(headings).size).toBe(headings.length);
  });

  it.each([
    "/does-not-exist",
    "/wizard/extra/segments",
    "/%C3%A7%C3%A3o",
  ])("unknown path %s redirects home rather than showing nothing", async (path) => {
    renderAt(path);
    // `replace` is deliberate: Back must not bounce the user into the dead URL again.
    const { path: settledPath, heading } = await settled();
    expect(settledPath).toBe("/");
    expect(heading).toBe(i18n.t("work.overview"));
  });

  /**
   * `/ANALYSIS` used to sit in the list above and "passed" — but only because an empty
   * session made AnalysisPage's own `<Navigate to="/">` guard fire. React Router compiles
   * every path with `caseSensitive: route.caseSensitive === true`, i.e. false by default
   * (react-router 8.3.0), so an uppercase URL matches the real route and never reaches the
   * catch-all. Asserted explicitly so that if someone opts into case-sensitive matching the
   * change is a deliberate, visible one rather than a silent redirect for existing links.
   */
  it("matches a path case-insensitively instead of treating it as unknown", async () => {
    renderAt("/ANALYSIS");
    const { path, heading } = await settled();
    expect(path).toBe("/ANALYSIS");
    expect(heading).toBe(i18n.t("analysis.title"));
  });

  it("declares no duplicate paths", () => {
    expect(new Set(APP_ROUTES).size).toBe(APP_ROUTES.length);
  });

  it("keeps the home route, which every unknown URL falls back to", () => {
    expect(APP_ROUTES).toContain("/");
  });
});
