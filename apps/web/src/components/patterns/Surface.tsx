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
  const v =
    variant === "flat"
      ? "bg-transparent"
      : variant === "inset"
        ? "border border-otm-border/60 bg-otm-surface-1/50 shadow-inner"
        : "border border-otm-border bg-otm-surface-2 shadow-otm-sm";
  return (
    <div className={`rounded-otm-md ${v} ${className}`} {...rest}>
      {children}
    </div>
  );
}
