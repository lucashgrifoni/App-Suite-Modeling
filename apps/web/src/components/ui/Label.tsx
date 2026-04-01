import type { LabelHTMLAttributes } from "react";

type LabelProps = LabelHTMLAttributes<HTMLLabelElement> & { htmlFor: string };

export function Label({ className = "", htmlFor, ...props }: Readonly<LabelProps>) {
  return (
    <label
      htmlFor={htmlFor}
      className={`mb-1 block text-sm font-medium text-otm-text-muted ${className}`}
      {...props}
    />
  );
}
