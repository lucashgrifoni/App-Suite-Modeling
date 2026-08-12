import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveApiPort, resolveApiProxyTarget } from "./devApiTarget";

/** Keeps the intentional fallback warnings out of the test output. */
function silenceWarnings() {
  return vi.spyOn(console, "warn").mockImplementation(() => {});
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("resolveApiProxyTarget", () => {
  it("defaults to loopback 8000 when nothing is set", () => {
    expect(resolveApiProxyTarget({})).toBe("http://127.0.0.1:8000");
  });

  it("uses 127.0.0.1 rather than localhost so an IPv4-only uvicorn is reachable", () => {
    // Regression guard: `localhost` can resolve to ::1 first on Windows, which
    // the `--host 127.0.0.1` backend refuses.
    expect(resolveApiProxyTarget({})).not.toContain("localhost");
  });

  it("honours OTM_API_PORT when port 8000 is already taken", () => {
    expect(resolveApiProxyTarget({ OTM_API_PORT: "8123" })).toBe("http://127.0.0.1:8123");
  });

  it("lets OTM_API_URL override the whole origin", () => {
    expect(resolveApiProxyTarget({ OTM_API_URL: "http://backend.internal:9000" })).toBe(
      "http://backend.internal:9000",
    );
  });

  it("prefers OTM_API_URL over OTM_API_PORT", () => {
    expect(resolveApiProxyTarget({ OTM_API_URL: "http://backend:9000", OTM_API_PORT: "8123" })).toBe(
      "http://backend:9000",
    );
  });

  it("trims surrounding whitespace", () => {
    expect(resolveApiProxyTarget({ OTM_API_PORT: "  8123  " })).toBe("http://127.0.0.1:8123");
    expect(resolveApiProxyTarget({ OTM_API_URL: "  http://backend:9000  " })).toBe("http://backend:9000");
  });

  it.each(["", "   ", "abc", "80a0", "-1", "0", "65536", "8000.5"])(
    "falls back to the default for the malformed port %j",
    (port) => {
      expect(resolveApiProxyTarget({ OTM_API_PORT: port })).toBe("http://127.0.0.1:8000");
    },
  );

  it("accepts the boundary ports 1 and 65535", () => {
    expect(resolveApiProxyTarget({ OTM_API_PORT: "1" })).toBe("http://127.0.0.1:1");
    expect(resolveApiProxyTarget({ OTM_API_PORT: "65535" })).toBe("http://127.0.0.1:65535");
  });

  it("ignores an empty OTM_API_URL instead of producing an empty target", () => {
    expect(resolveApiProxyTarget({ OTM_API_URL: "   ", OTM_API_PORT: "8123" })).toBe("http://127.0.0.1:8123");
  });

  it("accepts an https origin", () => {
    expect(resolveApiProxyTarget({ OTM_API_URL: "https://api.example.test" })).toBe(
      "https://api.example.test",
    );
  });

  // Only OTM_API_PORT was validated. A malformed OTM_API_URL was handed to Vite verbatim,
  // which then reported `getaddrinfo ENOTFOUND base.invalid` — a host the developer never
  // set and cannot grep for — while every API call 502'd. The docs and this module's own
  // docstring both promise the malformed case falls back to the default.
  it.each([
    "127.0.0.1:8331", // scheme omitted, the shape OTM_API_PORT teaches
    "8331", // just a port
    "not a url at all",
    "ftp://backend:9000", // parses, but not a proxyable scheme
    "//backend:9000", // protocol-relative
    "http://", // no host
  ])("falls back to the default for the malformed OTM_API_URL %j", (url) => {
    silenceWarnings();
    expect(resolveApiProxyTarget({ OTM_API_URL: url })).toBe("http://127.0.0.1:8000");
  });

  it("still honours a valid OTM_API_PORT when OTM_API_URL is malformed", () => {
    silenceWarnings();
    expect(resolveApiProxyTarget({ OTM_API_URL: "8331", OTM_API_PORT: "8123" })).toBe(
      "http://127.0.0.1:8123",
    );
  });

  it("names OTM_API_URL in the warning rather than leaving the developer with base.invalid", () => {
    const warn = silenceWarnings();
    resolveApiProxyTarget({ OTM_API_URL: "127.0.0.1:8331" });
    expect(warn.mock.calls[0][0]).toContain("OTM_API_URL");
  });

  it("does not warn when OTM_API_URL is valid", () => {
    const warn = silenceWarnings();
    resolveApiProxyTarget({ OTM_API_URL: "http://backend:9000" });
    expect(warn).not.toHaveBeenCalled();
  });
});

describe("resolveApiPort", () => {
  it("defaults to 8000", () => {
    expect(resolveApiPort({})).toBe("8000");
  });

  it("honours a valid override", () => {
    expect(resolveApiPort({ OTM_API_PORT: "8123" })).toBe("8123");
  });

  it("falls back to the default for a malformed override", () => {
    expect(resolveApiPort({ OTM_API_PORT: "nope" })).toBe("8000");
  });

  it("stays consistent with the proxy target so uvicorn and Vite never disagree", () => {
    const env = { OTM_API_PORT: "8123" };
    expect(resolveApiProxyTarget(env)).toBe(`http://127.0.0.1:${resolveApiPort(env)}`);
  });
});
