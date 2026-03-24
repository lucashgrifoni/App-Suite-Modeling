export function Alert({
  variant = "error",
  children,
}: {
  variant?: "error" | "info";
  children: React.ReactNode;
}) {
  const styles =
    variant === "error"
      ? "border-red-200 bg-red-50 text-red-900"
      : "border-sky-200 bg-sky-50 text-sky-900";
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${styles}`} role="alert">
      {children}
    </div>
  );
}
