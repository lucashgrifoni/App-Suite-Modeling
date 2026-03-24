import type { ButtonHTMLAttributes } from "react";

const variants = {
  primary:
    "bg-[var(--asm-primary)] text-white hover:bg-[var(--asm-primary-strong)] shadow-sm disabled:opacity-50",
  secondary:
    "bg-white text-slate-800 border border-[var(--asm-border)] hover:bg-slate-50 disabled:opacity-50",
  ghost: "text-slate-700 hover:bg-slate-100 disabled:opacity-50",
  danger: "bg-[var(--asm-danger)] text-white hover:opacity-90 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
