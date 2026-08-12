/**
 * Resolves the origin the Vite dev/preview proxy forwards `/api` to.
 *
 * Port 8000 is one of the most contended ports on a developer machine, and the
 * hybrid E2E stack (`playwright.hybrid.config.ts`) binds uvicorn to it. When
 * something else already holds 8000 the whole no-mock E2E path dies with an
 * opaque bind error, so the origin has to be overridable without editing
 * tracked config files.
 *
 * The target defaults to `127.0.0.1`, not `localhost`: uvicorn is started with
 * `--host 127.0.0.1`, and on Windows `localhost` can resolve to `::1` first,
 * which the IPv4-only listener refuses. `vite.config.ts` already carries the
 * mirror-image of this note for the dev server's own listen address.
 */

const DEFAULT_API_PORT = "8000";

/** Highest valid TCP port; 0 is excluded because it means "any free port". */
const MAX_PORT = 65535;

function isValidPort(value: string): boolean {
  if (!/^\d+$/.test(value)) return false;
  const port = Number(value);
  return port >= 1 && port <= MAX_PORT;
}

/**
 * @param env Process environment (pass `process.env` from a config file).
 *   - `OTM_API_URL` wins outright and is used verbatim, so a remote or
 *     containerised backend can be targeted.
 *   - `OTM_API_PORT` overrides only the port on the loopback default.
 *   Malformed values fall back to the default rather than producing a target
 *   that silently fails to connect.
 */
export function resolveApiProxyTarget(env: Record<string, string | undefined>): string {
  const explicitUrl = env.OTM_API_URL?.trim();
  if (explicitUrl) return explicitUrl;

  const requestedPort = env.OTM_API_PORT?.trim();
  const port = requestedPort && isValidPort(requestedPort) ? requestedPort : DEFAULT_API_PORT;

  return `http://127.0.0.1:${port}`;
}

/** The port the hybrid E2E stack should bind uvicorn to. */
export function resolveApiPort(env: Record<string, string | undefined>): string {
  const requestedPort = env.OTM_API_PORT?.trim();
  return requestedPort && isValidPort(requestedPort) ? requestedPort : DEFAULT_API_PORT;
}
