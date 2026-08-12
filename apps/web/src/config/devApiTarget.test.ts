import { describe, expect, it } from "vitest";

import { resolveApiPort, resolveApiProxyTarget } from "./devApiTarget";

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
