import { useId } from "react";
import { useTheme, type ThemePreference } from "../../context/ThemeContext";

const OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: "dark", label: "Escuro" },
  { value: "light", label: "Claro" },
  { value: "system", label: "Sistema" },
];

export function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  const id = useId();

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="sr-only">
        Tema da interface
      </label>
      <select
        id={id}
        value={preference}
        onChange={(e) => setPreference(e.target.value as ThemePreference)}
        className="rounded-full border border-otm-border bg-otm-surface-2 px-2 py-1.5 text-xs font-medium text-otm-text focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)]"
      >
        {OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
