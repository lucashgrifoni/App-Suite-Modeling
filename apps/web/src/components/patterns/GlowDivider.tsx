export function GlowDivider({ className = "" }: Readonly<{ className?: string }>) {
  return (
    <div
      className={`relative my-8 h-px w-full overflow-visible ${className}`}
      role="separator"
      aria-hidden
    >
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-otm-accent/35 to-transparent blur-sm" />
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-otm-mint-300/25 to-transparent" />
    </div>
  );
}
