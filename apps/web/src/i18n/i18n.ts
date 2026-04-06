import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ptBR from "./locales/pt-BR.json";
import {
  getInitialLocaleFromWindow,
  LOCALE_STORAGE_KEY,
  parseStoredLocale,
  type SupportedLocale,
} from "./localePolicy";

const resources = {
  en: { translation: en },
  "pt-BR": { translation: ptBR },
} as const;

/**
 * Inicialização síncrona com recursos embutidos (sem lazy-load) para previsibilidade e bundle simples.
 */
void i18n.use(initReactI18next).init({
  resources,
  lng: typeof window !== "undefined" ? getInitialLocaleFromWindow() : "en",
  fallbackLng: "en",
  supportedLngs: ["pt-BR", "en"],
  interpolation: {
    escapeValue: true,
  },
  returnNull: false,
  returnEmptyString: false,
  parseMissingKeyHandler: (key: string) => {
    if (import.meta.env.DEV) {
      console.warn(`[i18n] missing key: ${key}`);
    }
    return key;
  },
});

if (typeof window !== "undefined") {
  i18n.on("languageChanged", (lng: string) => {
    const safe = parseStoredLocale(lng) ?? ("en" as SupportedLocale);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, safe);
    } catch {
      /* quota / private mode */
    }
  });
}

/**
 * Troca de idioma com validação estrita (apenas allowlist).
 */
export function changeLocale(next: string): Promise<SupportedLocale> {
  const safe = parseStoredLocale(next) ?? "en";
  return i18n.changeLanguage(safe).then(() => safe);
}

export default i18n;
