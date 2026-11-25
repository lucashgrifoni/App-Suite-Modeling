import { createElement, lazy, type ComponentType, type LazyExoticComponent } from "react";

/**
 * A code-split route that survives a dropped chunk request.
 *
 * `React.lazy` calls its loader exactly once and memoises the resulting promise — including
 * a rejected one. One failed request for a route's JavaScript chunk therefore removed that
 * page from the running application: navigating away and back re-rendered the same rejected
 * payload without issuing a single new request, so the error boundary reappeared with the
 * network long since healthy. Only a full browser reload recovered it. On a flaky mobile
 * link or behind a CDN blip, one dropped packet cost the user the page.
 *
 * Two defences, in order:
 *
 *  1. The loader retries once, after a short pause. The dominant cause is a single dropped
 *     request, and the second attempt simply succeeds — the user sees no failure at all.
 *  2. If both attempts fail the route is registered as recoverable, and the next time the
 *     user leaves the broken screen its memoised `lazy()` is thrown away. Coming back
 *     builds a fresh one and fetches the chunk again.
 *
 * Step 2 is deliberately driven from OUTSIDE the failed subtree, by
 * `resetFailedChunkRoutes`, and this is the part that is easy to get wrong. Discarding the
 * payload at the moment of failure looks equivalent and is not: a component that suspends
 * never commits, so React re-renders it from scratch after the rejection, a fresh `lazy()`
 * is built, the import runs again, fails again — an unbounded request loop aimed at a
 * network that is already failing. Measured at seven requests in 1.5 s before this was
 * bound to a navigation instead.
 */

type RouteModule = Readonly<{ default: ComponentType }>;
type RouteLoader = () => Promise<RouteModule>;

/**
 * Pause before the single retry. Long enough that a momentary blip has passed, short enough
 * that a user who is about to see the error boundary is not left staring at a skeleton.
 */
export const CHUNK_RETRY_DELAY_MS = 400;

/** Routes whose chunk could not be fetched, and the callback that lets them try again. */
const recoverable = new Set<() => void>();

/**
 * Let every route that failed to load fetch its chunk again on its next visit.
 *
 * Called when a screen that crashed is torn down — see `ErrorBoundary` — because that is
 * the one moment that means "the user has moved on" without also meaning "React is
 * retrying the render it just failed".
 */
export function resetFailedChunkRoutes(): void {
  for (const rebuild of recoverable) rebuild();
  recoverable.clear();
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export function lazyRoute(load: RouteLoader): ComponentType {
  let memoized: LazyExoticComponent<ComponentType> | null = null;

  function discard() {
    memoized = null;
  }

  async function loadWithRetry(): Promise<RouteModule> {
    try {
      return await load();
    } catch {
      await delay(CHUNK_RETRY_DELAY_MS);
      try {
        return await load();
      } catch (retryError) {
        // Both attempts are spent. The rejected payload stays in place so React stops here
        // and shows the error boundary; it is dropped only once the user leaves.
        recoverable.add(discard);
        throw retryError;
      }
    }
  }

  function LazyRoute() {
    memoized ??= lazy(loadWithRetry);
    return createElement(memoized);
  }
  LazyRoute.displayName = "LazyRoute";
  return LazyRoute;
}
