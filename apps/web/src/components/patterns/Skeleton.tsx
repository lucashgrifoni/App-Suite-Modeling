import type { HTMLAttributes } from "react";

export function Skeleton({
  className = "",
  ...rest
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      aria-hidden
      className={`relative overflow-hidden rounded-md bg-otm-surface-3 ${className}`}
      {...rest}
    >
      <div
        className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent motion-reduce:animate-none"
        aria-hidden
      />
    </div>
  );
}

export function SkeletonText({ lines = 3 }: Readonly<{ lines?: number }>) {
  const rows = Array.from({ length: lines }, (_, i) => ({
    id: `skeleton-row-${i}`,
    width: i === lines - 1 ? "w-2/3" : "w-full",
  }));
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {rows.map((row) => (
        <Skeleton key={row.id} className={`h-3 ${row.width}`} />
      ))}
    </div>
  );
}
