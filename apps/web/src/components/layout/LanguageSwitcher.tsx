import { useId } from "react";
import { useTranslation } from "react-i18next";
import { changeLocale } from "../../i18n/i18n";
import type { SupportedLocale } from "../../i18n/localePolicy";

const OPTIONS: SupportedLocale[] = ["pt-BR", "en"];

/**
 * Seletor de idioma (allowlist fixa) alinhado ao estilo do ThemeToggle — sem alterar layout global.
 */
export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const id = useId();
  const current = (i18n.resolvedLanguage ?? i18n.language) as SupportedLocale;

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="sr-only">
        {t("language.label")}
      </label>
      <select
        id={id}
        data-testid="language-switcher"
        aria-label={t("language.label")}
        value={OPTIONS.includes(current) ? current : "en"}
        onChange={(e) => void changeLocale(e.target.value)}
        className="rounded-full border border-otm-border bg-otm-surface-2 px-2 py-1.5 text-xs font-medium text-otm-text focus:outline-none focus:ring-2 focus:ring-[color:var(--otm-ring)]"
      >
        {OPTIONS.map((lng) => (
          <option key={lng} value={lng}>
            {lng === "pt-BR" ? t("language.ptBR") : t("language.en")}
          </option>
        ))}
      </select>
    </div>
  );
}
