const prefix = import.meta.env.VITE_API_PREFIX ?? "/api";

/**
 * Ceiling for a single API round trip.
 *
 * `fetch` has no default timeout. A backend that accepts the TCP connection and then never
 * answers leaves the promise pending indefinitely, which on screen is a button stuck on
 * "Analyzing…", disabled, with no error, no cancel and no way out but a page reload — the
 * user cannot even tell "slow" from "dead". 30 s is far past the slowest observed
 * analyze/export round trip while still failing soon enough to be actionable.
 */
export const DEFAULT_TIMEOUT_MS = 30_000;

/** Report rendering is measurably heavier than the JSON routes, so it gets more room. */
export const REPORT_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  status: number;
  body: unknown;
  /**
   * True when `message` came from the server's own error envelope rather than from the
   * HTTP reason phrase. A gateway 502 has an empty body, so its message is the bare word
   * "Bad Gateway" — useless to a user and worth replacing with real guidance.
   */
  fromServerDetail: boolean;

  constructor(message: string, status: number, body: unknown, fromServerDetail = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.fromServerDetail = fromServerDetail;
  }
}

/**
 * A 2xx whose body is not the JSON document the route promises.
 *
 * `parseJson` returns the raw text when a body is not JSON, and `null` when it is empty;
 * both used to be handed to the caller as a successful result. Everything that answers 200
 * without being this API does exactly that — an SPA-fallback static host serving
 * `index.html` for `/api/...`, a captive portal, a gateway pointed at the wrong upstream —
 * so "Analysis generated." was announced (and a History snapshot written) for a run that
 * never happened, and `items.map is not a function` took the Templates page down into the
 * global error boundary. For the person at the screen, reaching something that is not this
 * API is the same situation as not reaching it at all, so it is reported the same way.
 */
export class ApiMalformedResponseError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`The ${status} response body was not the JSON this endpoint returns`);
    this.name = "ApiMalformedResponseError";
    this.status = status;
  }
}

/** The request was cut off by `DEFAULT_TIMEOUT_MS`, not answered by the server. */
export class ApiTimeoutError extends Error {
  readonly timeoutMs: number;

  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = "ApiTimeoutError";
    this.timeoutMs = timeoutMs;
  }
}

/**
 * `fetch` with a hard deadline. Every request the app makes goes through this, so no code
 * path can accidentally opt out of the timeout.
 *
 * The deadline covers connect-plus-response-headers, which is the case that actually
 * strands the UI: a backend that accepts the socket and never replies. Once headers land,
 * the caller owns the body and the timer is released — a server that streams headers and
 * then stalls mid-body is not bounded here.
 */
export async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (e) {
    if (controller.signal.aborted) throw new ApiTimeoutError(timeoutMs);
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

function parseJsonText(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function getObjectField(value: unknown, field: string): unknown {
  if (typeof value !== "object" || value === null) return undefined;
  if (!(field in value)) return undefined;
  return (value as Record<string, unknown>)[field];
}

function getStringField(value: unknown, field: string): string | undefined {
  const v = getObjectField(value, field);
  return typeof v === "string" ? v : undefined;
}

function safeStringify(value: unknown): string | undefined {
  try {
    return JSON.stringify(value);
  } catch {
    return undefined;
  }
}

function formatPydanticErrors(errors: unknown): string | undefined {
  if (!Array.isArray(errors) || errors.length === 0) return undefined;
  const lines: string[] = [];
  for (const item of errors) {
    if (typeof item !== "object" || item === null) continue;
    const o = item as Record<string, unknown>;
    const msg = typeof o.msg === "string" ? o.msg : null;
    if (!msg) continue;
    const loc = Array.isArray(o.loc)
      ? o.loc
          .map((x) => (typeof x === "string" || typeof x === "number" ? String(x) : ""))
          .filter(Boolean)
          .join(".")
      : "";
    lines.push(loc ? `${loc}: ${msg}` : msg);
  }
  return lines.length ? lines.join("\n") : undefined;
}

/**
 * The API's unhandled-exception handler answers `{code, message, request_id}` at the TOP
 * level, while every other handler nests the same envelope under `detail`. Reading only
 * `detail` meant a 500 carried no server message at all and fell back to `res.statusText`,
 * so the screen read "Internal Server Error" while the body held the server's own sentence
 * and the `request_id` that is the only handle on the matching server log line.
 *
 * Recognised narrowly: only an object carrying BOTH a string `code` and a string `message`,
 * and only after the caller has established there is no `detail` to prefer, so an unrelated
 * body cannot be mistaken for an error envelope.
 */
function topLevelEnvelope(data: unknown): string | undefined {
  const code = getStringField(data, "code");
  const message = getStringField(data, "message");
  if (code === undefined || message === undefined) return undefined;
  return `${code}: ${message}`;
}

/** The server's own description of the failure, or `undefined` if it sent none. */
function extractApiErrorMessage(data: unknown): string | undefined {
  const detail = getObjectField(data, "detail");
  if (detail === undefined) return topLevelEnvelope(data);
  if (typeof detail === "string") return detail;

  const message = getStringField(detail, "message");
  const code = getStringField(detail, "code");
  const pydantic = formatPydanticErrors(getObjectField(detail, "errors"));

  let head: string | undefined;
  if (message && code) head = `${code}: ${message}`;
  else if (message) head = message;
  else head = safeStringify(detail);

  if (head === undefined) return undefined;
  if (pydantic) return `${head}\n\n${pydantic}`;
  return head;
}

/**
 * The `ApiError` for a non-2xx response, built from its raw body text.
 *
 * Shared by every caller so no route can grow its own error path. `fetchPremiumReport` had
 * one: it re-read `detail.message` by hand and then handed the ApiError the raw *text* as
 * `body`, so the presentation layer — which reads the envelope off `body` to reword a code
 * or list field violations — saw a string and fell through to the bare message. The premium
 * report route is exactly where a coded, actionable envelope matters most (`PDF_DEPENDENCY`
 * tells the user the server cannot render PDFs and that two working alternatives sit on the
 * same page), and it was the one route that could not present one.
 */
export function apiErrorFromResponseText(
  status: number,
  statusText: string,
  text: string,
): ApiError {
  const data = parseJsonText(text);
  const detailMessage = extractApiErrorMessage(data);
  return new ApiError(detailMessage ?? statusText, status, data, detailMessage !== undefined);
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown; timeoutMs?: number },
): Promise<T> {
  const { json, headers, timeoutMs, ...rest } = init ?? {};
  const url = path.startsWith("http") ? path : `${prefix}${path}`;
  const res = await fetchWithTimeout(
    url,
    {
      ...rest,
      headers: {
        ...(json === undefined ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      body: json === undefined ? rest.body : JSON.stringify(json),
    },
    timeoutMs,
  );
  const text = await res.text();
  // Every route reachable through `apiFetch` answers with a JSON object or array, so
  // anything else on a 2xx is not an answer from this API. See ApiMalformedResponseError.
  if (res.ok) {
    const data = parseJsonText(text);
    if (typeof data !== "object" || data === null) throw new ApiMalformedResponseError(res.status);
    return data as T;
  }

  throw apiErrorFromResponseText(res.status, res.statusText, text);
}
