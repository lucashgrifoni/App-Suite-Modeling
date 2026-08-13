import type { TFunction } from "i18next";
import { ApiError, ApiMalformedResponseError, ApiTimeoutError } from "./client";

/**
 * Statuses a proxy, gateway or load balancer emits when it cannot reach the backend at
 * all. The API itself never returns these, and their bodies are empty, so the only message
 * available from the response is the raw HTTP reason phrase — "Bad Gateway" on its own,
 * which names neither the cause nor a next step.
 */
const GATEWAY_STATUSES: ReadonlySet<number> = new Set([502, 503, 504]);

/**
 * Pydantic renders a `pattern=` violation as `String should match pattern '<regex>'`, and
 * the regex went straight to the screen. `ENTITY_ID_PATTERN` is the only pattern in the
 * canonical schema, so the rule behind it can be stated in words instead. Kept in step with
 * `OTM_ENTITY_ID_REGEX` in utils/documentNormalize.
 */
const PATTERN_VIOLATION = /^String should match pattern /;

/**
 * Pydantic prefixes every message raised by a custom validator with `Value error, `. It is
 * the library naming its own exception class, and it reached the screen in front of the
 * sentence the validator actually wrote: "components: Value error, duplicate id in
 * components". Nothing after the comma changes, so only the prefix is dropped.
 */
const PYDANTIC_VALUE_ERROR_PREFIX = /^Value error, /;

function objectField(value: unknown, field: string): unknown {
  if (typeof value !== "object" || value === null) return undefined;
  return (value as Record<string, unknown>)[field];
}

function stringField(value: unknown, field: string): string | undefined {
  const v = objectField(value, field);
  return typeof v === "string" ? v : undefined;
}

/** The `{code, message, errors?}` envelope, or `undefined` when the body is not one. */
function errorEnvelope(error: ApiError): Record<string, unknown> | undefined {
  const detail = objectField(error.body, "detail");
  if (typeof detail !== "object" || detail === null || Array.isArray(detail)) return undefined;
  return detail as Record<string, unknown>;
}

/**
 * Server codes whose own `message` is not written for the person reading it, and which the
 * UI therefore words itself.
 *
 * The YAML/JSON import path interpolates the PyYAML parser's exception verbatim, so a
 * malformed upload arrived as `while parsing a flow sequence in "<unicode string>", line 1,
 * column 7:` — library-internal wording, caret markers flattened onto one line, and the
 * user's own file echoed back — sitting next to sibling errors from the same endpoint
 * (IMPORT_EMPTY_ARTIFACT, IMPORT_NOT_UTF8) that are clean, actionable sentences.
 *
 * Deliberately an allowlist: every other code keeps the server's message, because the API
 * owns the explanation and second-guessing it here would hide real detail.
 */
const REWORDED_CODES: ReadonlySet<string> = new Set(["IMPORT_ARTIFACT_INVALID"]);

function localizedCodeMessage(code: string | undefined, t: TFunction): string | undefined {
  if (!code || !REWORDED_CODES.has(code)) return undefined;
  return t(`apiErrors.codes.${code}`);
}

/** `["body", "components", 0, "id"]` → `components[1].id`: 1-based, like the rows on screen. */
function locationLabel(loc: unknown): string {
  if (!Array.isArray(loc)) return "";
  const parts: string[] = [];
  for (const segment of loc) {
    if (typeof segment === "number") {
      const last = parts.length - 1;
      if (last >= 0) parts[last] = `${parts[last]}[${segment + 1}]`;
    } else if (typeof segment === "string" && segment !== "body") {
      parts.push(segment);
    }
  }
  return parts.join(".");
}

function violationLabel(msg: string, t: TFunction): string {
  if (PATTERN_VIOLATION.test(msg)) return t("apiErrors.entityIdPattern");
  return msg.replace(PYDANTIC_VALUE_ERROR_PREFIX, "");
}

/** One readable line per field the server rejected. */
function fieldViolations(detail: Record<string, unknown>, t: TFunction): string[] {
  const errors = detail.errors;
  if (!Array.isArray(errors)) return [];
  const lines: string[] = [];
  for (const item of errors) {
    const msg = stringField(item, "msg");
    if (!msg) continue;
    const where = locationLabel(objectField(item, "loc"));
    const what = violationLabel(msg, t);
    lines.push(where ? `${where}: ${what}` : what);
  }
  return lines;
}

function describeEnvelope(
  error: ApiError,
  detail: Record<string, unknown>,
  t: TFunction,
): string {
  const code = stringField(detail, "code");
  const message = stringField(detail, "message");
  const localized = localizedCodeMessage(code, t);
  let head: string;
  if (localized !== undefined) head = localized;
  else if (message !== undefined && code !== undefined) head = `${code}: ${message}`;
  else head = message ?? error.message;

  const fields = fieldViolations(detail, t);
  return fields.length === 0 ? head : `${head}\n\n${fields.join("\n")}`;
}

/**
 * Turn anything thrown by the API layer into a message worth putting in front of a user.
 *
 * Precedence: a timeout is described as a timeout; a gateway failure with no server body,
 * and a 2xx that did not come from this API at all, are described as the backend being
 * unreachable — which is the user's actual situation; a coded envelope the UI can word better
 * is reworded (and its field violations humanised); anything else the server actually
 * explained is shown as the server explained it; and anything else falls back to the
 * caller's own key, which is the operation that failed ("Could not run the analysis").
 */
export function apiErrorMessage(error: unknown, t: TFunction, fallbackKey: string): string {
  if (error instanceof ApiTimeoutError) return t("apiErrors.timeout");
  if (error instanceof ApiMalformedResponseError) return t("apiErrors.unreachable");
  if (error instanceof ApiError) {
    if (!error.fromServerDetail && GATEWAY_STATUSES.has(error.status)) {
      return t("apiErrors.unreachable");
    }
    const detail = errorEnvelope(error);
    return detail ? describeEnvelope(error, detail, t) : error.message;
  }
  return t(fallbackKey);
}
