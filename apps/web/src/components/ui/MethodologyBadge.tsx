import type { MethodologyId } from "../../types/methodology";

const SHORT: Partial<Record<MethodologyId, string>> = {
  stride: "STRIDE",
  linddun: "LINDDUN",
  nist_data_centric: "NIST DC",
  octave_allegro: "OCTAVE",
  cia_die: "CIA",
  pasta: "PASTA",
  plot4ai: "PLOT4ai",
};

export function MethodologyBadge({
  id,
  className = "",
}: Readonly<{ id: MethodologyId; className?: string }>) {
  const label = SHORT[id] ?? id;
  return (
    <span
      className={`inline-flex items-center rounded-md border border-otm-border-strong bg-otm-primary-subtle px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-otm-accent ${className}`}
    >
      {label}
    </span>
  );
}
