import type { DragEvent, ReactNode } from "react";
import { useTranslation } from "react-i18next";

export function FileDropZone({
  onFile,
  disabled,
  description,
  children,
  className = "",
}: Readonly<{
  onFile: (file: File) => void;
  disabled?: boolean;
  description?: ReactNode;
  children?: ReactNode;
  className?: string;
}>) {
  const { t } = useTranslation();

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f) onFile(f);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
      onDrop={handleDrop}
      className={`group relative overflow-hidden rounded-otm-xl border-2 border-dashed border-otm-border-control bg-otm-primary-muted px-6 py-10 text-center transition duration-otm ${disabled ? "pointer-events-none opacity-50" : ""} ${className}`}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(86,255,149,0.08), transparent 60%)",
        }}
        aria-hidden
      />
      <div className="relative space-y-2">
        <p className="font-display text-sm font-semibold text-otm-text">{t("fileDrop.dragHere")}</p>
        {description ? <p className="text-xs text-otm-text-muted">{description}</p> : null}
        {children}
      </div>
    </div>
  );
}
