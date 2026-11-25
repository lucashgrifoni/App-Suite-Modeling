import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

export function WorkflowGuide({
  variant = "full",
  className = "",
}: Readonly<{ variant?: "full" | "compact"; className?: string }>) {
  const { t } = useTranslation();

  const steps = useMemo(
    () =>
      [
        { id: "import", labelKey: "workflow.import", to: "/import", hintKey: "workflow.hintImport" },
        { id: "wizard", labelKey: "workflow.wizard", to: "/wizard", hintKey: "workflow.hintWizard" },
        { id: "review", labelKey: "workflow.review", to: "/review", hintKey: "workflow.hintReview" },
        { id: "analysis", labelKey: "workflow.analysis", to: "/analysis", hintKey: "workflow.hintAnalysis" },
        { id: "export", labelKey: "workflow.export", to: "/export", hintKey: "workflow.hintExport" },
        { id: "diff", labelKey: "workflow.diff", to: "/diff", hintKey: "workflow.hintDiff" },
      ] as const,
    [],
  );

  if (variant === "compact") {
    return (
      <nav
        aria-label={t("workflow.ariaRecommended")}
        className={`flex flex-wrap items-center gap-1 text-xs text-otm-text-muted ${className}`}
      >
        {steps.map((s, i) => (
          <span key={s.id} className="flex items-center gap-1">
            {i > 0 ? <span aria-hidden className="text-otm-text-subtle">→</span> : null}
            <Link to={s.to} className="font-medium text-otm-accent underline-offset-2 hover:underline">
              {t(s.labelKey)}
            </Link>
          </span>
        ))}
      </nav>
    );
  }

  return (
    <section aria-labelledby="workflow-guide-title" className={className}>
      <h2 id="workflow-guide-title" className="font-display text-lg font-semibold text-otm-text">
        {t("workflow.pipelineTitle")}
      </h2>
      <p className="mt-1 max-w-3xl text-sm text-otm-text-muted">{t("workflow.pipelineDesc")}</p>
      <ol className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {steps.map((s, idx) => (
          <li key={s.id}>
            <Link
              to={s.to}
              className="flex h-full flex-col rounded-otm-md border border-otm-border px-3 py-3 shadow-otm-sm transition duration-otm hover:border-otm-border-strong hover:shadow-otm-glow focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--otm-ring)]"
            >
              <span className="text-[10px] font-semibold uppercase tracking-wider text-otm-text-subtle">
                {String(idx + 1).padStart(2, "0")}
              </span>
              <span className="mt-1 font-display text-sm font-semibold text-otm-text">{t(s.labelKey)}</span>
              <span className="mt-0.5 text-[11px] leading-snug text-otm-text-muted">{t(s.hintKey)}</span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
