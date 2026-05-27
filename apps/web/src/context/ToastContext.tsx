import {
  createContext,
  useCallback,
  useContext,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";

export type ToastVariant = "success" | "error" | "warning" | "info";

/**
 * Toast ids are React keys for ephemeral UI notifications — not a security token.
 * Prefer `crypto.randomUUID()` when available; otherwise a monotonic counter keeps
 * ids collision-free without `Math.random()` (which Sonar flags as weak crypto).
 */
let toastSeq = 0;
function nextToastId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  toastSeq += 1;
  return `toast-${Date.now()}-${toastSeq}`;
}

export interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastApi {
  push: (message: string, variant?: ToastVariant, durationMs?: number) => void;
  success: (message: string, durationMs?: number) => void;
  error: (message: string, durationMs?: number) => void;
  warning: (message: string, durationMs?: number) => void;
  info: (message: string, durationMs?: number) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: "border-emerald-500/40 bg-emerald-950/90 text-emerald-100",
  error: "border-red-500/40 bg-red-950/90 text-red-100",
  warning: "border-amber-500/40 bg-amber-950/90 text-amber-100",
  info: "border-sky-500/40 bg-sky-950/90 text-sky-100",
};

function ToastViewport({
  toasts,
  onDismiss,
  reducedMotion,
  titleId,
  regionLabel,
  closeLabel,
}: Readonly<{
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
  reducedMotion: boolean;
  titleId: string;
  regionLabel: string;
  closeLabel: string;
}>) {
  if (toasts.length === 0) return null;
  return (
    <section
      className="pointer-events-none fixed bottom-4 right-4 z-[200] flex max-h-[min(40vh,320px)] w-[min(100vw-2rem,22rem)] flex-col gap-2 p-0 sm:bottom-6 sm:right-6"
      aria-labelledby={titleId}
    >
      <span id={titleId} className="sr-only">
        {regionLabel}
      </span>
      <ul className="pointer-events-auto flex flex-col gap-2" aria-live="polite" aria-relevant="additions text">
        {toasts.map((t) => (
          <li
            key={t.id}
            className={`rounded-otm-md border px-3 py-2.5 text-sm shadow-otm-lg backdrop-blur-sm transition duration-otm ease-otm ${
              reducedMotion ? "" : "motion-safe:animate-page-enter"
            } ${VARIANT_STYLES[t.variant]}`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="leading-snug">{t.message}</p>
              <button
                type="button"
                className="shrink-0 rounded p-0.5 text-xs opacity-80 hover:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--otm-ring)]"
                onClick={() => onDismiss(t.id)}
                aria-label={closeLabel}
              >
                ×
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ToastProvider({ children }: Readonly<{ children: ReactNode }>) {
  const { t } = useTranslation();
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, number>>(new Map());
  const reducedMotion = usePrefersReducedMotion();
  const titleId = useId();

  const dismiss = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t !== undefined) {
      globalThis.clearTimeout(t);
      timers.current.delete(id);
    }
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (message: string, variant: ToastVariant = "info", durationMs = 5200) => {
      const id = nextToastId();
      setToasts((prev) => [...prev.slice(-4), { id, message, variant }]);
      const tid = globalThis.setTimeout(() => dismiss(id), durationMs);
      timers.current.set(id, tid);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      push,
      success: (m, d) => push(m, "success", d),
      error: (m, d) => push(m, "error", d),
      warning: (m, d) => push(m, "warning", d),
      info: (m, d) => push(m, "info", d),
      dismiss,
    }),
    [push, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport
        toasts={toasts}
        onDismiss={dismiss}
        reducedMotion={reducedMotion}
        titleId={titleId}
        regionLabel={t("toast.regionLabel")}
        closeLabel={t("toast.close")}
      />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast outside ToastProvider");
  return ctx;
}
