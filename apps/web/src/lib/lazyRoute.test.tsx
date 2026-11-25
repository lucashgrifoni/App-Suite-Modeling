/**
 * One dropped chunk request used to remove a route from the application for the rest of the
 * session.
 *
 * Measured on the production build: aborting the FIRST request for the Wizard chunk put the
 * error boundary on screen, and clicking away to another page and back showed the identical
 * error while the abort counter stayed at 1 — no second request was ever issued, because
 * `React.lazy` had memoised the rejected promise. Only a full browser reload recovered it.
 *
 * Every test here therefore counts LOADER CALLS, not just rendered output: "it worked the
 * second time" only means something if a second attempt actually happened. The real
 * `ErrorBoundary` is used rather than a stand-in, because it owns half the fix — leaving a
 * screen that crashed is what lets the route try again.
 */

import { Suspense } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { lazyRoute } from "./lazyRoute";
import { ErrorBoundary } from "../components/error/ErrorBoundary";
import i18n from "../i18n/i18n";

function Page() {
  return <p>page content</p>;
}

/** Time for the two attempts plus the pause between them, with room to spare. */
const SETTLE_MS = 3000;

/**
 * Mount the route the way the app does: inside a Suspense fallback and, above it, an error
 * boundary that the layout rebuilds on every navigation.
 */
function mount(Route: React.ComponentType) {
  return render(
    <ErrorBoundary>
      <Suspense fallback={<p>loading</p>}>
        <Route />
      </Suspense>
    </ErrorBoundary>,
  );
}

function findPage() {
  return screen.findByText("page content", undefined, { timeout: SETTLE_MS });
}

function findBoundary() {
  return screen.findByText(i18n.t("errorBoundary.title"), undefined, { timeout: SETTLE_MS });
}

/** A chunk request that fails for the first `failures` attempts, then succeeds. */
function flakyLoader(failures: number) {
  let attempts = 0;
  return vi.fn(async () => {
    attempts += 1;
    if (attempts <= failures) {
      throw new TypeError("error loading dynamically imported module: /assets/WizardPage.js");
    }
    return { default: Page };
  });
}

describe("lazyRoute", () => {
  // React logs every caught render error; the failure paths here are deliberate.
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the page when the chunk loads", async () => {
    mount(lazyRoute(flakyLoader(0)));
    expect(await findPage()).toBeInTheDocument();
  });

  it("imports the chunk only once when it loads first time", async () => {
    const load = flakyLoader(0);
    mount(lazyRoute(load));
    await findPage();
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("retries once, so a single dropped request never reaches the user", async () => {
    mount(lazyRoute(flakyLoader(1)));
    expect(await findPage()).toBeInTheDocument();
  });

  it("issues a real second request rather than replaying the first result", async () => {
    const load = flakyLoader(1);
    mount(lazyRoute(load));
    await findPage();
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("shows the error boundary when the chunk is genuinely gone", async () => {
    mount(lazyRoute(flakyLoader(Number.POSITIVE_INFINITY)));
    expect(await findBoundary()).toBeInTheDocument();
  });

  /**
   * The trap this design exists to avoid. A rejected payload makes React re-render the
   * subtree, and a component that suspended never committed — so discarding the memoised
   * `lazy()` at the moment of failure means the re-render builds a new one and imports
   * again, forever. Seven requests in 1.5 s, measured, before the rebuild was bound to a
   * navigation instead.
   */
  it("stops after the retry instead of hammering a network that is already down", async () => {
    const load = flakyLoader(Number.POSITIVE_INFINITY);
    mount(lazyRoute(load));
    await findBoundary();
    await new Promise((r) => setTimeout(r, 600));
    expect(load).toHaveBeenCalledTimes(2);
  });

  /** The reported defect: navigate away, come back with the network healthy. */
  it("recovers on the next visit once the network is healthy", async () => {
    const Route = lazyRoute(flakyLoader(2));

    const first = mount(Route);
    await findBoundary();
    first.unmount();

    mount(Route);
    expect(await findPage()).toBeInTheDocument();
  });

  it("actually re-requests the chunk on that next visit", async () => {
    const load = flakyLoader(2);
    const Route = lazyRoute(load);

    const first = mount(Route);
    await findBoundary();
    expect(load).toHaveBeenCalledTimes(2);
    first.unmount();

    mount(Route);
    await findPage();
    expect(load).toHaveBeenCalledTimes(3);
  });

  it("does not re-import a chunk it already has", async () => {
    const load = flakyLoader(0);
    const Route = lazyRoute(load);

    const first = mount(Route);
    await findPage();
    first.unmount();

    mount(Route);
    await findPage();
    expect(load).toHaveBeenCalledTimes(1);
  });

  /**
   * Leaving a screen that did NOT fail must not invalidate anything: an unrelated route
   * that loaded fine keeps its module, so ordinary navigation costs no extra requests.
   */
  it("leaves a healthy route alone when another screen is torn down", async () => {
    const healthy = flakyLoader(0);
    const HealthyRoute = lazyRoute(healthy);

    const first = mount(HealthyRoute);
    await findPage();
    first.unmount();

    const broken = mount(lazyRoute(flakyLoader(Number.POSITIVE_INFINITY)));
    await findBoundary();
    broken.unmount();

    mount(HealthyRoute);
    await findPage();
    expect(healthy).toHaveBeenCalledTimes(1);
  });
});
