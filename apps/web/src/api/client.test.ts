import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./client";

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
});
