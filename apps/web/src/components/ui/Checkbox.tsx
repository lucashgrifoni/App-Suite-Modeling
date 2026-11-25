import type { InputHTMLAttributes } from "react";

export function Checkbox({ className = "", ...props }: Readonly<InputHTMLAttributes<HTMLInputElement>>) {
  return (
    <input
      type="checkbox"
      className={`h-4 w-4 rounded border-otm-border-control bg-otm-surface-1 text-otm-primary accent-[var(--otm-primary)] focus:ring-2 focus:ring-[color:var(--otm-ring)] focus:ring-offset-0 focus:ring-offset-transparent ${className}`}
      {...props}
    />
  );
}
