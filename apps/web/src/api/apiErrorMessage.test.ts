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
import { ApiError, ApiMalformedResponseError, ApiTimeoutError } from "./client";

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

  it("describes a 200 that did not come from this API as unreachable", () => {
    // A static host with SPA fallback answers `/api/v1/templates` with index.html, 200.
    // The user's situation is the same as a dead backend, so the guidance is the same.
    expect(apiErrorMessage(new ApiMalformedResponseError(200), t, "analysis.toastFail")).toBe(
      "t:apiErrors.unreachable",
    );
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

/**
 * Two more error paths reached users as raw machine output.
 *
 * A malformed YAML upload came back as the PyYAML parser's own exception — internal wording
 * (`while parsing a flow sequence in "<unicode string>"`), caret markers flattened onto one
 * line, and the user's file content echoed back — while the sibling errors from the very
 * same endpoint (IMPORT_EMPTY_ARTIFACT, IMPORT_NOT_UTF8) are clean, actionable sentences.
 * And a schema violation printed Pydantic's raw `String should match pattern '<regex>'`
 * against a 0-based path (`components.0.id`) that matches nothing visible in the UI.
 */
describe("apiErrorMessage envelope presentation", () => {
  function envelope(code: string, message: string, errors?: unknown[]): ApiError {
    const detail: Record<string, unknown> = { code, message };
    if (errors) detail.errors = errors;
    return new ApiError(`${code}: ${message}`, 422, { detail }, true);
  }

  it("replaces a raw parser exception with the UI's own wording", () => {
    const err = envelope(
      "IMPORT_ARTIFACT_INVALID",
      'Não foi possível interpretar como YAML/JSON: while parsing a flow sequence in "<unicode string>", line 1, column 7',
    );

    expect(apiErrorMessage(err, t, "import.toastFail")).toBe(
      "t:apiErrors.codes.IMPORT_ARTIFACT_INVALID",
    );
  });

  it("does not echo the library's internal wording back to the user", () => {
    const err = envelope(
      "IMPORT_ARTIFACT_INVALID",
      'Não foi possível interpretar como YAML/JSON: while parsing a flow sequence in "<unicode string>"',
    );

    expect(apiErrorMessage(err, t, "import.toastFail")).not.toContain("<unicode string>");
  });

  it("keeps the server's own message for a code the UI has no wording for", () => {
    const err = envelope("PACK_NOT_FOUND", "industry pack 'nope' not found");

    expect(apiErrorMessage(err, t, "analysis.toastFail")).toBe(
      "PACK_NOT_FOUND: industry pack 'nope' not found",
    );
  });

  it("states the id rule instead of printing the raw regex", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      {
        loc: ["body", "components", 0, "id"],
        msg: "String should match pattern '^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$'",
      },
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).not.toContain("a-zA-Z0-9_");
  });

  it("names the offending field with a 1-based row, as the UI shows it", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      {
        loc: ["body", "components", 0, "id"],
        msg: "String should match pattern '^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$'",
      },
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toContain(
      "components[1].id: t:apiErrors.entityIdPattern",
    );
  });

  it("keeps a violation that already reads as a sentence", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      { loc: ["body", "metadata", "title"], msg: "Field required" },
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toContain(
      "metadata.title: Field required",
    );
  });

  it("still shows the headline above the field list", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      { loc: ["body", "metadata", "title"], msg: "Field required" },
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toContain(
      "DOCUMENT_VALIDATION_ERROR: Schema violation.",
    );
  });

  it("keeps a violation the server reported without a location", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      { msg: "Model is empty" },
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toContain("Model is empty");
  });

  it("ignores entries in `errors` that carry no message", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      { loc: ["body", "metadata"] },
      "not an object",
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toBe(
      "DOCUMENT_VALIDATION_ERROR: Schema violation.",
    );
  });

  it("falls back to the transport message when the envelope carries only a code", () => {
    const err = new ApiError("Unprocessable Content", 422, { detail: { code: "ODD" } }, true);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toBe("Unprocessable Content");
  });

  it("uses a bare `message` when the envelope carries no code", () => {
    const err = new ApiError("x", 422, { detail: { message: "Payload too large." } }, true);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toBe("Payload too large.");
  });

  it("leaves a string `detail` alone", () => {
    const err = new ApiError("Nope.", 413, { detail: "Nope." }, true);

    expect(apiErrorMessage(err, t, "import.toastFail")).toBe("Nope.");
  });

  it("leaves an array `detail` alone", () => {
    const err = new ApiError("raw", 422, { detail: [{ msg: "bad" }] }, true);

    expect(apiErrorMessage(err, t, "import.toastFail")).toBe("raw");
  });

  it("drops a leading numeric segment that names no field", () => {
    const err = envelope("DOCUMENT_VALIDATION_ERROR", "Schema violation.", [
      { loc: [0, "id"], msg: "Field required" },
    ]);

    expect(apiErrorMessage(err, t, "wizard.validationFail")).toContain("id: Field required");
  });
});
