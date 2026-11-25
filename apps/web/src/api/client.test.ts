import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  ApiMalformedResponseError,
  ApiTimeoutError,
  apiErrorFromResponseText,
  apiFetch,
  fetchWithTimeout,
} from "./client";

function mockFetch(status: number, body: string, ok = status < 400) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: `HTTP ${status}`,
    text: () => Promise.resolve(body),
  } as Response);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiFetch", () => {
  it("parses a JSON success body", async () => {
    vi.stubGlobal("fetch", mockFetch(200, JSON.stringify({ ok: true, n: 2 })));
    const data = await apiFetch<{ ok: boolean; n: number }>("/health");
    expect(data).toEqual({ ok: true, n: 2 });
  });

  /**
   * These three replace an earlier test that asserted an empty 2xx body "returns null for
   * an empty success body". That was the defect written down as the specification: every
   * route behind `apiFetch` answers with a JSON object or array, so `null` was never a
   * result any caller could use — the analyze handler took it as a successful run and
   * announced "Analysis generated." while storing nothing, and TemplatesPage called `.map`
   * on it and crashed into the global error boundary.
   */
  it("rejects an empty 2xx body instead of calling it a result", async () => {
    vi.stubGlobal("fetch", mockFetch(200, ""));
    await expect(apiFetch("/noop")).rejects.toBeInstanceOf(ApiMalformedResponseError);
  });

  it("rejects a 2xx body that is HTML, as an SPA-fallback host serves", async () => {
    vi.stubGlobal("fetch", mockFetch(200, "<!doctype html><title>app</title>"));
    await expect(apiFetch("/v1/templates")).rejects.toBeInstanceOf(ApiMalformedResponseError);
  });

  it("rejects truncated JSON on a 2xx", async () => {
    vi.stubGlobal("fetch", mockFetch(200, '{"items": [{"id": "a", "titl'));
    await expect(apiFetch("/v1/templates")).rejects.toBeInstanceOf(ApiMalformedResponseError);
  });

  it("names the status it received so the failure is diagnosable", async () => {
    vi.stubGlobal("fetch", mockFetch(200, "null"));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiMalformedResponseError;
    expect(err.status).toBe(200);
  });

  it("still accepts a JSON array, which the templates list is", async () => {
    vi.stubGlobal("fetch", mockFetch(200, JSON.stringify([{ id: "a" }])));
    await expect(apiFetch("/v1/templates")).resolves.toEqual([{ id: "a" }]);
  });

  it("serialises a `json` option as the body with a JSON content-type", async () => {
    const f = mockFetch(200, "{}");
    vi.stubGlobal("fetch", f);
    await apiFetch("/x", { method: "POST", json: { a: 1 } });
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.body).toBe(JSON.stringify({ a: 1 }));
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("throws an ApiError carrying status + parsed body on failure", async () => {
    vi.stubGlobal("fetch", mockFetch(404, JSON.stringify({ detail: "missing" })));
    const err = await apiFetch("/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, message: "missing", body: { detail: "missing" } });
  });

  it("formats `{detail:{code,message}}` as 'code: message'", async () => {
    vi.stubGlobal("fetch", mockFetch(400, JSON.stringify({ detail: { code: "BAD_INPUT", message: "boom" } })));
    await expect(apiFetch("/x")).rejects.toThrow("BAD_INPUT: boom");
  });

  it("appends pydantic-style field errors to the message", async () => {
    const body = JSON.stringify({
      detail: { message: "Validation failed", errors: [{ loc: ["body", "title"], msg: "field required" }] },
    });
    vi.stubGlobal("fetch", mockFetch(422, body));
    await expect(apiFetch("/x")).rejects.toThrow(/Validation failed[\s\S]*body\.title: field required/);
  });

  it("falls back to statusText when the error body is not JSON", async () => {
    vi.stubGlobal("fetch", mockFetch(500, "<html>nope</html>"));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.status).toBe(500);
    expect(err.message).toBe("HTTP 500");
    expect(err.body).toBe("<html>nope</html>");
  });

  it("marks a message that came from the server's own error envelope", async () => {
    vi.stubGlobal("fetch", mockFetch(422, JSON.stringify({ detail: { message: "bad" } })));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.fromServerDetail).toBe(true);
  });

  it("marks a message that is only the HTTP reason phrase", async () => {
    // The distinction the "Bad Gateway" fix rests on: an empty body means the response
    // told the user nothing, so the UI must supply the explanation itself.
    vi.stubGlobal("fetch", mockFetch(502, ""));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.fromServerDetail).toBe(false);
  });

  it("passes an abort signal to fetch so a hung request can be cut off", async () => {
    const f = mockFetch(200, "{}");
    vi.stubGlobal("fetch", f);
    await apiFetch("/x");
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });
});

/**
 * The API's unhandled-exception handler answers `{code, message, request_id}` at the top
 * level; every other handler nests that envelope under `detail`. Reading only `detail` left
 * a 500 with no server message at all, so the UI showed `res.statusText` — a bare "Internal
 * Server Error" — and discarded the `request_id` that correlates the failure with the log.
 */
describe("apiFetch top-level error envelope", () => {
  const INTERNAL_500 = JSON.stringify({
    code: "INTERNAL_ERROR",
    message: "An unexpected error occurred.",
    request_id: "adadde6c-5ec1-4285-8cf5-3b84b3f54fe2",
  });

  it("reads the server's sentence out of a 500 instead of the reason phrase", async () => {
    vi.stubGlobal("fetch", mockFetch(500, INTERNAL_500));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.message).toBe("INTERNAL_ERROR: An unexpected error occurred.");
  });

  it("marks that message as the server's own, not a reason-phrase fallback", async () => {
    vi.stubGlobal("fetch", mockFetch(500, INTERNAL_500));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.fromServerDetail).toBe(true);
  });

  it("keeps the request id on the error for the presentation layer", async () => {
    vi.stubGlobal("fetch", mockFetch(500, INTERNAL_500));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.body).toMatchObject({ request_id: "adadde6c-5ec1-4285-8cf5-3b84b3f54fe2" });
  });

  it("leaves a body that is not the envelope shape to the reason phrase", async () => {
    // `code` without `message` is not an error envelope, so nothing is invented from it.
    vi.stubGlobal("fetch", mockFetch(503, JSON.stringify({ code: "upstream" })));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.message).toBe("HTTP 503");
  });

  it("still prefers a nested `detail` envelope when the body has both", async () => {
    const body = JSON.stringify({ code: "OUTER", message: "outer", detail: { message: "inner" } });
    vi.stubGlobal("fetch", mockFetch(400, body));
    const err = (await apiFetch("/x").catch((e: unknown) => e)) as ApiError;
    expect(err.message).toBe("inner");
  });
});

/**
 * `fetchPremiumReport` cannot use `apiFetch` — it reads a PDF or Markdown body, not JSON —
 * so it had its own hand-rolled error path that handed `ApiError` the raw response TEXT as
 * `body`. Everything that presents an error reads the envelope off `body`, so a string
 * meant none of it applied: the route that answers 501 `PDF_DEPENDENCY` was the one route
 * whose coded envelope could never reach the screen.
 */
describe("apiErrorFromResponseText", () => {
  it("parses the body so the envelope reaches the presentation layer", () => {
    const body = JSON.stringify({ detail: { code: "PDF_DEPENDENCY", message: "install it" } });
    const err = apiErrorFromResponseText(501, "Not Implemented", body);
    expect(err.body).toEqual({ detail: { code: "PDF_DEPENDENCY", message: "install it" } });
  });

  it("composes the message the same way every other route does", () => {
    const body = JSON.stringify({ detail: { code: "PDF_DEPENDENCY", message: "install it" } });
    expect(apiErrorFromResponseText(501, "Not Implemented", body).message).toBe(
      "PDF_DEPENDENCY: install it",
    );
  });

  it("keeps the status so a 501 is not confused with a gateway failure", () => {
    const err = apiErrorFromResponseText(501, "Not Implemented", "{}");
    expect(err.status).toBe(501);
  });

  it("falls back to the reason phrase when the body is not JSON", () => {
    const err = apiErrorFromResponseText(502, "Bad Gateway", "");
    expect(err.message).toBe("Bad Gateway");
  });

  it("marks a reason-phrase fallback as not coming from the server", () => {
    expect(apiErrorFromResponseText(502, "Bad Gateway", "").fromServerDetail).toBe(false);
  });
});

/**
 * `fetch` has no default timeout. A backend that accepts the connection and never answers
 * left "Analyzing…" disabled forever, with no error and no cancel — only a page reload got
 * the user out.
 */
describe("fetchWithTimeout", () => {
  /** A backend that accepts the request and never responds. */
  function blackHoleFetch() {
    return vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        }),
    );
  }

  it("rejects with ApiTimeoutError once the deadline passes", async () => {
    vi.stubGlobal("fetch", blackHoleFetch());
    await expect(fetchWithTimeout("/x", {}, 10)).rejects.toBeInstanceOf(ApiTimeoutError);
  });

  it("reports the deadline it enforced", async () => {
    vi.stubGlobal("fetch", blackHoleFetch());
    const err = (await fetchWithTimeout("/x", {}, 10).catch(
      (e: unknown) => e,
    )) as ApiTimeoutError;
    expect(err.timeoutMs).toBe(10);
  });

  it("resolves normally when the server answers in time", async () => {
    vi.stubGlobal("fetch", mockFetch(200, "{}"));
    await expect(fetchWithTimeout("/x", {}, 5_000)).resolves.toMatchObject({ status: 200 });
  });

  it("re-throws a network failure unchanged rather than calling it a timeout", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchWithTimeout("/x", {}, 5_000)).rejects.toBeInstanceOf(TypeError);
  });

  it("clears its timer so a fast response leaves nothing pending", async () => {
    const clear = vi.spyOn(globalThis, "clearTimeout");
    vi.stubGlobal("fetch", mockFetch(200, "{}"));
    await fetchWithTimeout("/x", {}, 5_000);
    expect(clear).toHaveBeenCalled();
  });
});
