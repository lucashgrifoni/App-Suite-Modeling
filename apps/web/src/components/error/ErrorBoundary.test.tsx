import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";
import i18n from "../../i18n/i18n";

function Boom(): never {
  throw new Error("kaboom");
}

/** A realistic failure: the wording a browser produces when a route chunk cannot load. */
function ChunkFailure(): never {
  throw new TypeError(
    "Failed to fetch dynamically imported module: http://127.0.0.1:4312/assets/WizardPage-CsLYIQKb.js",
  );
}

describe("ErrorBoundary", () => {
  // React logs caught render errors to console.error; silence it for clean output.
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders children when nothing throws", () => {
    render(
      <ErrorBoundary>
        <p>safe content</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("safe content")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("raises an alert when a child throws", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  /**
   * This replaces a test that asserted the panel shows "kaboom" — the defect written down
   * as the specification. The raw `error.message` is a library or engine string: a chunk
   * failure rendered as "Failed to fetch dynamically imported module: /assets/
   * WizardPage-CsLYIQKb.js", hashed filename and all, and Firefox words the identical fault
   * differently again. The translated sentence existed but sat behind `error.message ||`,
   * so it only ever appeared for an error with an empty message — i.e. effectively never.
   */
  it("leads with a human sentence rather than the raw exception", () => {
    render(
      <ErrorBoundary>
        <ChunkFailure />
      </ErrorBoundary>,
    );
    expect(screen.getByText(i18n.t("errorBoundary.fallback"))).toBeInTheDocument();
  });

  it("does not put the hashed asset URL in the panel's own copy", () => {
    render(
      <ErrorBoundary>
        <ChunkFailure />
      </ErrorBoundary>,
    );
    const summary = screen.getByText(i18n.t("errorBoundary.detailsSummary"));
    const details = summary.closest("details");
    expect(details).not.toBeNull();
    // The raw text is inside the disclosure, so it is not part of what the panel says.
    expect(details).toHaveTextContent("WizardPage-CsLYIQKb.js");
  });

  it("still keeps the raw message reachable for whoever needs it", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText("kaboom")).toBeInTheDocument();
  });

  it("offers both recovery actions", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("button", { name: i18n.t("errorBoundary.reload") })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: i18n.t("errorBoundary.home") })).toBeInTheDocument();
  });

  it("omits the disclosure when the error carries no message", () => {
    function Empty(): never {
      throw new Error("");
    }
    render(
      <ErrorBoundary>
        <Empty />
      </ErrorBoundary>,
    );
    expect(screen.queryByText(i18n.t("errorBoundary.detailsSummary"))).toBeNull();
  });
});

/**
 * The boundary is keyed on the pathname by the layout, so leaving a screen that crashed
 * tears it down. That unmount is what lets a route whose chunk failed to download try
 * again; the end-to-end proof lives in lib/lazyRoute.test.tsx, which mounts this very
 * boundary. Asserted here only as "tearing it down is safe in both states".
 */
describe("ErrorBoundary unmount", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("tears down cleanly after a failure", () => {
    const view = render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(() => view.unmount()).not.toThrow();
  });

  it("tears down cleanly when nothing failed", () => {
    const view = render(
      <ErrorBoundary>
        <p>safe content</p>
      </ErrorBoundary>,
    );
    expect(() => view.unmount()).not.toThrow();
  });
});
