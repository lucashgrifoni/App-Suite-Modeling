import type { ButtonHTMLAttributes } from "react";

const variants = {
  primary:
    "bg-gradient-to-r from-otm-primary to-otm-accent text-otm-green-950 shadow-otm-sm hover:brightness-110 active:scale-[0.98] active:brightness-95 disabled:opacity-50 disabled:active:scale-100",
  secondary:
    "border border-otm-border-strong bg-otm-surface-2 text-otm-text hover:border-otm-mint-400/40 hover:bg-otm-surface-3 active:scale-[0.99] disabled:opacity-50",
  ghost:
    "text-otm-text-muted hover:bg-otm-primary-muted hover:text-otm-text active:scale-[0.99] disabled:opacity-50",
  danger:
    "bg-red-600/90 text-white hover:bg-red-600 active:scale-[0.98] disabled:opacity-50",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-otm-md px-4 py-2 text-sm font-semibold transition duration-otm ease-otm motion-reduce:transition-none motion-reduce:active:scale-100 ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
