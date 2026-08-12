import type { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  /**
   * Marca o campo como inválido: pinta a fronteira e o anel de foco com
   * --otm-danger e expõe aria-invalid. A mensagem de erro é do chamador —
   * ligue-a com aria-describedby para satisfazer WCAG 3.3.1.
   */
  invalid?: boolean;
};

const BASE =
  "w-full rounded-otm-md border bg-otm-surface-1 px-3 py-2 text-sm text-otm-text placeholder:text-otm-text-subtle transition duration-otm ease-otm focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60";

// --otm-border-control garante os 3:1 da WCAG 1.4.11 na fronteira do controlo;
// --otm-border (1.27:1) deixava o campo sem limite percetível no tema escuro.
const RESTING =
  "border-otm-border-control focus:border-otm-mint-400/50 focus:ring-[color:var(--otm-ring)]";

const INVALID =
  "border-otm-danger focus:border-otm-danger focus:ring-[color:var(--otm-danger)]";

export function Input({ className = "", invalid = false, ...props }: Readonly<InputProps>) {
  return (
    <input
      aria-invalid={invalid || undefined}
      className={`${BASE} ${invalid ? INVALID : RESTING} ${className}`}
      {...props}
    />
  );
}
