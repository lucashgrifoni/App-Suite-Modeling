type AlertProps = {
  variant?: "error" | "info" | "warning" | "success";
  children: React.ReactNode;
};

export function Alert({ variant = "error", children }: Readonly<AlertProps>) {
  const styles =
    variant === "error"
      ? "border-red-500/35 bg-red-500/10 text-red-100"
      : variant === "info"
        ? "border-sky-500/35 bg-sky-500/10 text-sky-950 dark:text-sky-100"
        : variant === "warning"
          ? "border-amber-500/35 bg-amber-500/10 text-amber-100"
          : "border-emerald-500/35 bg-emerald-500/10 text-emerald-100";
  return (
    <div className={`rounded-otm-md border px-4 py-3 text-sm leading-relaxed ${styles}`} role="alert">
      {children}
    </div>
  );
}
