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

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const { json, headers, ...rest } = init ?? {};
  const url = path.startsWith("http") ? path : `${prefix}${path}`;
  const res = await fetch(url, {
    ...rest,
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  const data = await parseJson(res);
  if (!res.ok) {
    const msg =
      typeof data === "object" && data !== null && "detail" in data
        ? JSON.stringify((data as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(msg, res.status, data);
  }
  return data as T;
}
