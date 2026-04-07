export function FrameworkTag({
  label,
  className = "",
}: Readonly<{ label: string; className?: string }>) {
  return (
    <span
      className={`inline-flex max-w-full items-center truncate rounded-md border border-otm-border bg-otm-surface-3 px-2 py-0.5 text-[11px] font-medium text-emerald-900 dark:text-otm-mint-300 ${className}`}
      title={label}
    >
      {label}
    </span>
  );
}
