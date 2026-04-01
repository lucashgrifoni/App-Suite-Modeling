import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: Readonly<InputHTMLAttributes<HTMLInputElement>>) {
  return (
    <input
      className={`w-full rounded-otm-md border border-otm-border bg-otm-surface-1 px-3 py-2 text-sm text-otm-text placeholder:text-otm-text-subtle transition duration-otm ease-otm focus:border-otm-mint-400/50 focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)] disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      {...props}
    />
  );
}
