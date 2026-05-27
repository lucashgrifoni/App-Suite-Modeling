import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "otm.web.themePreference";

export type ThemePreference = "dark" | "light" | "system";

export function resolveEffectiveTheme(preference: ThemePreference): "dark" | "light" {
  if (preference === "dark") return "dark";
  if (preference === "light") return "light";
  if (globalThis.window === undefined || !globalThis.matchMedia) return "dark";
  return globalThis.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function readStoredPreference(): ThemePreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") return raw;
  } catch {
    /* ignore */
  }
  return "dark";
}

function applyDomTheme(effective: "dark" | "light") {
  document.documentElement.dataset.theme = effective;
}

interface ThemeState {
  preference: ThemePreference;
  effective: "dark" | "light";
  setPreference: (p: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

export function ThemeProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredPreference());
  const [effective, setEffective] = useState<"dark" | "light">(() =>
    resolveEffectiveTheme(readStoredPreference()),
  );

  useEffect(() => {
    const e = resolveEffectiveTheme(preference);
    setEffective(e);
    applyDomTheme(e);
  }, [preference]);

  useEffect(() => {
    if (preference !== "system") return;
    const mq = globalThis.matchMedia("(prefers-color-scheme: light)");
    const sync = () => {
      const e = resolveEffectiveTheme("system");
      setEffective(e);
      applyDomTheme(e);
    };
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, [preference]);

  const changePreference = useCallback((p: ThemePreference) => {
    setPreference(p);
    try {
      localStorage.setItem(STORAGE_KEY, p);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(
    () => ({
      preference,
      effective,
      setPreference: changePreference,
    }),
    [preference, effective, changePreference],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme outside ThemeProvider");
  return ctx;
}
