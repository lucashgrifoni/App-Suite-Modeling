import { useTranslation } from "react-i18next";

export function Stepper({
  steps,
  currentIndex,
  /**
   * Highest step the user may jump to. Defaults to the current step, which is the
   * strictly-forward behaviour; pass a higher value when steps stay unlocked once their
   * work is done, so stepping back does not re-lock everything ahead.
   */
  maxReachableIndex,
  onStepClick,
}: Readonly<{
  steps: readonly { id: number; label: string }[];
  currentIndex: number;
  maxReachableIndex?: number;
  onStepClick?: (index: number) => void;
}>) {
  const { t } = useTranslation();
  const reachable = Math.max(maxReachableIndex ?? currentIndex, currentIndex);
  return (
    <nav aria-label={t("wizard.stepperAria")} className="w-full">
      <ol className="flex flex-wrap gap-2">
        {steps.map((s, i) => {
          const active = i === currentIndex;
          const clickable = Boolean(onStepClick) && i <= reachable;
          let stateClass: string;
          if (active) {
            stateClass = "bg-gradient-to-r from-otm-primary to-otm-accent text-otm-green-950 shadow-otm-glow";
          } else if (clickable) {
            // Behind the cursor or unlocked ahead of it: either way the user can go there,
            // so it must not be painted as a dead step.
            stateClass = "border border-otm-border-strong bg-otm-surface-3 text-otm-text hover:border-otm-mint-400/40";
          } else {
            stateClass = "cursor-not-allowed border border-otm-border bg-otm-surface-1/60 text-otm-text-subtle";
          }
          return (
            <li key={s.id}>
              <button
                type="button"
                disabled={!clickable}
                onClick={() => clickable && onStepClick?.(i)}
                className={`group relative overflow-hidden rounded-full px-3.5 py-1.5 text-xs font-semibold transition duration-otm ease-otm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--otm-ring)] ${stateClass}`}
              >
                <span className="relative z-10">
                  {i + 1}. {s.label}
                </span>
                {active ? (
                  <span
                    className="pointer-events-none absolute inset-0 opacity-40"
                    style={{
                      background:
                        "linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.25) 50%, transparent 100%)",
                    }}
                    aria-hidden
                  />
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
