import type { HTMLAttributes } from "react";

export function Skeleton({
  className = "",
  ...rest
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      role="presentation"
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
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={`h-3 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
      ))}
    </div>
  );
}
