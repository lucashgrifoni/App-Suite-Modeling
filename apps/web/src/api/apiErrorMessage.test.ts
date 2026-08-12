/**
 * Two error paths reached users as raw protocol noise.
 *
 * A backend outage arrived as the bare HTTP reason phrase — an alert reading exactly
 * "Bad Gateway", inlined into the templates catalogue — because the proxy's 502 has an
 * empty body and the client fell back to `res.statusText`. And an unresponsive backend
 * produced no message at all: `fetch` has no timeout, so the request simply never settled.
 */

import { describe, expect, it } from "vitest";
import { apiErrorMessage } from "./apiErrorMessage";
import { ApiError, ApiTimeoutError } from "./client";

/** Stand-in for i18next's `t`: echoes the key so assertions name the string chosen. */
const t = ((key: string) => `t:${key}`) as unknown as Parameters<typeof apiErrorMessage>[1];

describe("apiErrorMessage", () => {
  it("names the timeout when the request was cut off", () => {
    expect(apiErrorMessage(new ApiTimeoutError(30_000), t, "analysis.toastFail")).toBe(
      "t:apiErrors.timeout",
    );
  });

  it("replaces a bodyless 502 with unreachable-backend guidance", () => {
    const err = new ApiError("Bad Gateway", 502, null, false);
    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe("t:apiErrors.unreachable");
  });

  it("treats a bodyless 503 the same way", () => {
    const err = new ApiError("Service Unavailable", 503, null, false);
    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe("t:apiErrors.unreachable");
  });

  it("treats a bodyless 504 the same way", () => {
    const err = new ApiError("Gateway Timeout", 504, null, false);
    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe("t:apiErrors.unreachable");
  });

  it("keeps a 503 the API itself explained", () => {
    // Only the *bodyless* gateway case is opaque; a server that described its own
    // failure said something the user should read.
    const err = new ApiError("Engine is warming up", 503, { detail: "x" }, true);
    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe("Engine is warming up");
  });

  it("keeps the server's message for an ordinary 4xx", () => {
    const err = new ApiError("SCHEMA_ERROR: title is required", 422, {}, true);
    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe("SCHEMA_ERROR: title is required");
  });

  it("keeps a bodyless 500, which is the API answering rather than a gateway failing", () => {
    const err = new ApiError("Internal Server Error", 500, null, false);
    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe("Internal Server Error");
  });

  it("falls back to the caller's key for a non-API failure", () => {
    expect(apiErrorMessage(new TypeError("boom"), t, "analysis.toastFail")).toBe(
      "t:analysis.toastFail",
    );
  });

  it("falls back to the caller's key for a thrown non-Error", () => {
    expect(apiErrorMessage("nope", t, "export.toastFail")).toBe("t:export.toastFail");
  });
});
