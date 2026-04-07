const prefix = import.meta.env.VITE_API_PREFIX ?? "/api";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
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

function formatApiErrorMessage(data: unknown, fallback: string): string {
  const detail = getObjectField(data, "detail");
  if (detail === undefined) return fallback;
  if (typeof detail === "string") return detail;

  const message = getStringField(detail, "message");
  const code = getStringField(detail, "code");
  const pydantic = formatPydanticErrors(getObjectField(detail, "errors"));

  let head: string;
  if (message && code) head = `${code}: ${message}`;
  else if (message) head = message;
  else head = safeStringify(detail) ?? fallback;

  if (pydantic) return `${head}\n\n${pydantic}`;
  return head;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const { json, headers, ...rest } = init ?? {};
  const url = path.startsWith("http") ? path : `${prefix}${path}`;
  const res = await fetch(url, {
    ...rest,
    headers: {
      ...(json === undefined ? {} : { "Content-Type": "application/json" }),
      ...headers,
    },
    body: json === undefined ? rest.body : JSON.stringify(json),
  });
  const data = await parseJson(res);
  if (res.ok) return data as T;

  const msg = formatApiErrorMessage(data, res.statusText);
  throw new ApiError(msg, res.status, data);
}
