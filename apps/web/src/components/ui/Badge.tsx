type BadgeProps = {
  children: React.ReactNode;
  tone?: "neutral" | "warn" | "ok" | "accent";
};

export function Badge({ children, tone = "neutral" }: Readonly<BadgeProps>) {
  const tones = {
    neutral: "bg-slate-100 text-slate-700",
    warn: "bg-amber-50 text-amber-900",
    ok: "bg-emerald-50 text-emerald-900",
    accent: "bg-sky-50 text-sky-900",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
