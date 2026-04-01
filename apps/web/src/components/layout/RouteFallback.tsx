import { Skeleton } from "../patterns/Skeleton";

/**
 * Fallback de Suspense alinhado ao shell: evita layout shift excessivo durante split de rotas.
 */
export function RouteFallback() {
  return (
    <div
      className="space-y-6 py-2"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="space-y-3">
        <Skeleton className="h-8 w-48 max-w-full rounded-md" />
        <Skeleton className="h-4 w-full max-w-xl rounded-md" />
        <Skeleton className="h-4 w-2/3 max-w-lg rounded-md" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-40 rounded-otm-xl" />
        <Skeleton className="h-40 rounded-otm-xl" />
      </div>
    </div>
  );
}
