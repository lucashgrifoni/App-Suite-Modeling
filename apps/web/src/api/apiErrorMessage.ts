import type { TFunction } from "i18next";
import { ApiError, ApiTimeoutError } from "./client";

/**
 * Statuses a proxy, gateway or load balancer emits when it cannot reach the backend at
 * all. The API itself never returns these, and their bodies are empty, so the only message
 * available from the response is the raw HTTP reason phrase — "Bad Gateway" on its own,
 * which names neither the cause nor a next step.
 */
const GATEWAY_STATUSES: ReadonlySet<number> = new Set([502, 503, 504]);

/**
 * Turn anything thrown by the API layer into a message worth putting in front of a user.
 *
 * Precedence: a timeout is described as a timeout; a gateway failure with no server body
 * is described as the backend being unreachable; anything the server actually explained is
 * shown as the server explained it; and anything else falls back to the caller's own
 * key, which is the operation that failed ("Could not run the analysis").
 */
export function apiErrorMessage(error: unknown, t: TFunction, fallbackKey: string): string {
  if (error instanceof ApiTimeoutError) return t("apiErrors.timeout");
  if (error instanceof ApiError) {
    if (!error.fromServerDetail && GATEWAY_STATUSES.has(error.status)) {
      return t("apiErrors.unreachable");
    }
    return error.message;
  }
  return t(fallbackKey);
}
