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

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
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

/** The server's own description of the failure, or `undefined` if it sent none. */
function extractApiErrorMessage(data: unknown): string | undefined {
  const detail = getObjectField(data, "detail");
  if (detail === undefined) return undefined;
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
  const data = await parseJson(res);
  if (res.ok) return data as T;

  const detailMessage = extractApiErrorMessage(data);
  throw new ApiError(
    detailMessage ?? res.statusText,
    res.status,
    data,
    detailMessage !== undefined,
  );
}
