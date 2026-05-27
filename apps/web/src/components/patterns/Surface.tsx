import type { HTMLAttributes, ReactNode } from "react";

export function Surface({
  children,
  variant = "raised",
  className = "",
  ...rest
}: Readonly<
  {
    children: ReactNode;
    variant?: "flat" | "raised" | "inset";
  } & HTMLAttributes<HTMLDivElement>
>) {
  const SURFACE_STYLES: Record<NonNullable<typeof variant>, string> = {
    flat: "bg-transparent",
    inset: "border border-otm-border/60 bg-otm-surface-1/50 shadow-inner",
    raised: "border border-otm-border bg-otm-surface-2 shadow-otm-sm",
  };
  const v = SURFACE_STYLES[variant];
  return (
    <div className={`rounded-otm-md ${v} ${className}`} {...rest}>
      {children}
    </div>
  );
}
