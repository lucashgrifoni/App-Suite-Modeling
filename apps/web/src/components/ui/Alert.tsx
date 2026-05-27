type AlertProps = {
  variant?: "error" | "info" | "warning" | "success";
  children: React.ReactNode;
  className?: string;
};

const ALERT_VARIANT_STYLES: Record<NonNullable<AlertProps["variant"]>, string> = {
  error: "border-red-500/35 bg-red-500/10 text-red-950 dark:text-red-100",
  info: "border-sky-500/35 bg-sky-500/10 text-sky-950 dark:text-sky-100",
  warning: "border-amber-500/35 bg-amber-500/10 text-amber-950 dark:text-amber-100",
  success: "border-emerald-500/35 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100",
};

export function Alert({ variant = "error", children, className = "" }: Readonly<AlertProps>) {
  const styles = ALERT_VARIANT_STYLES[variant];
  return (
    <div
      className={`rounded-otm-md border px-4 py-3 text-sm leading-relaxed ${styles} ${className}`.trim()}
      role="alert"
    >
      {children}
    </div>
  );
}
