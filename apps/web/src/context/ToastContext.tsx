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
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";

export type ToastVariant = "success" | "error" | "warning" | "info";

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
}: Readonly<{
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
  reducedMotion: boolean;
  titleId: string;
}>) {
  if (toasts.length === 0) return null;
  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[200] flex max-h-[min(40vh,320px)] w-[min(100vw-2rem,22rem)] flex-col gap-2 p-0 sm:bottom-6 sm:right-6"
      aria-labelledby={titleId}
      role="region"
    >
      <span id={titleId} className="sr-only">
        Notificações
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
                aria-label="Fechar notificação"
              >
                ×
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ToastProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, number>>(new Map());
  const reducedMotion = usePrefersReducedMotion();
  const titleId = useId();

  const dismiss = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t !== undefined) {
      window.clearTimeout(t);
      timers.current.delete(id);
    }
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (message: string, variant: ToastVariant = "info", durationMs = 5200) => {
      const id =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setToasts((prev) => [...prev.slice(-4), { id, message, variant }]);
      const tid = window.setTimeout(() => dismiss(id), durationMs);
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
      <ToastViewport toasts={toasts} onDismiss={dismiss} reducedMotion={reducedMotion} titleId={titleId} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast outside ToastProvider");
  return ctx;
}
