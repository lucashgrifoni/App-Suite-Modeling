import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, ApiTimeoutError, apiFetch, fetchWithTimeout } from "./client";

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

  it("returns null for an empty success body", async () => {
    vi.stubGlobal("fetch", mockFetch(204, ""));
    await expect(apiFetch("/noop")).resolves.toBeNull();
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
