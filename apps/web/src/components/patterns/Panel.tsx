import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
  padded = true,
}: Readonly<{ children: ReactNode; className?: string; padded?: boolean }>) {
  return (
    <div
      className={`rounded-otm-lg border border-otm-border shadow-otm-sm backdrop-blur-sm ${padded ? "p-5" : ""} ${className}`}
    >
      {children}
    </div>
  );
}
