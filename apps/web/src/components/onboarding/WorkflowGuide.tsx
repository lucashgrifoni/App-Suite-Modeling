import { Link } from "react-router-dom";

const STEPS = [
  { id: "import", label: "Importar", to: "/import", hint: "OpenAPI, TF, K8s" },
  { id: "wizard", label: "Assistente", to: "/wizard", hint: "Modelo canónico" },
  { id: "review", label: "Diagrama", to: "/review", hint: "Rever fluxos" },
  { id: "analysis", label: "Análise", to: "/analysis", hint: "Motor + risco" },
  { id: "export", label: "Exportar", to: "/export", hint: "Artefactos" },
  { id: "diff", label: "Diff", to: "/diff", hint: "Comparar versões" },
] as const;

export function WorkflowGuide({
  variant = "full",
  className = "",
}: Readonly<{ variant?: "full" | "compact"; className?: string }>) {
  if (variant === "compact") {
    return (
      <nav
        aria-label="Fluxo recomendado"
        className={`flex flex-wrap items-center gap-1 text-xs text-otm-text-muted ${className}`}
      >
        {STEPS.map((s, i) => (
          <span key={s.id} className="flex items-center gap-1">
            {i > 0 ? <span aria-hidden className="text-otm-text-subtle">→</span> : null}
            <Link to={s.to} className="font-medium text-otm-accent underline-offset-2 hover:underline">
              {s.label}
            </Link>
          </span>
        ))}
      </nav>
    );
  }

  return (
    <section aria-labelledby="workflow-guide-title" className={className}>
      <h2 id="workflow-guide-title" className="font-display text-lg font-semibold text-otm-text">
        Pipeline técnico
      </h2>
      <p className="mt-1 max-w-3xl text-sm text-otm-text-muted">
        Do artefacto ao relatório: cada etapa valida ou enriquece o modelo no servidor antes da análise.
      </p>
      <ol className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {STEPS.map((s, idx) => (
          <li key={s.id}>
            <Link
              to={s.to}
              className="flex h-full flex-col rounded-otm-md border border-otm-border bg-otm-surface-2/80 px-3 py-3 shadow-otm-sm transition duration-otm hover:border-otm-border-strong hover:shadow-otm-glow focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--otm-ring)]"
            >
              <span className="text-[10px] font-semibold uppercase tracking-wider text-otm-text-subtle">
                {String(idx + 1).padStart(2, "0")}
              </span>
              <span className="mt-1 font-display text-sm font-semibold text-otm-text">{s.label}</span>
              <span className="mt-0.5 text-[11px] leading-snug text-otm-text-muted">{s.hint}</span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
