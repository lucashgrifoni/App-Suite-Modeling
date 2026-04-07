import type { SelectHTMLAttributes } from "react";

export function Select({ className = "", ...props }: Readonly<SelectHTMLAttributes<HTMLSelectElement>>) {
  return (
    <select
      className={`w-full rounded-otm-md border border-otm-border-strong bg-otm-surface-1 px-3 py-2 text-sm text-otm-text shadow-sm shadow-slate-900/5 transition duration-otm ease-otm focus:border-otm-mint-400/50 focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)] disabled:cursor-not-allowed disabled:opacity-60 dark:shadow-none ${className}`}
      {...props}
    />
  );
}
