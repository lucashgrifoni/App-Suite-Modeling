import { useId, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useTheme, type ThemePreference } from "../../context/ThemeContext";

export function ThemeToggle() {
  const { t } = useTranslation();
  const { preference, setPreference } = useTheme();
  const id = useId();

  const options = useMemo(
    (): { value: ThemePreference; label: string }[] => [
      { value: "dark", label: t("theme.dark") },
      { value: "light", label: t("theme.light") },
      { value: "system", label: t("theme.system") },
    ],
    [t],
  );

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="sr-only">
        {t("theme.label")}
      </label>
      <select
        id={id}
        value={preference}
        onChange={(e) => setPreference(e.target.value as ThemePreference)}
        className="rounded-full border border-otm-border bg-otm-surface-2 px-2 py-1.5 text-xs font-medium text-otm-text focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)]"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
