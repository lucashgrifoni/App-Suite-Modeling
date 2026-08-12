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
  lng: "window" in globalThis ? getInitialLocaleFromWindow() : "en",
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

/**
 * Keep `<html lang>` in step with the interface language.
 *
 * `index.html` ships a static `lang="en"` and nothing ever rewrote it, so switching the UI
 * to Portuguese left the entire page declared as English while rendering Portuguese — a
 * WCAG 2.2 SC 3.1.1 (Language of Page) failure that makes a screen reader read Portuguese
 * with an English voice and misleads browser translation offers. The theme already keeps
 * root-element state in sync (`documentElement.dataset.theme`); the language now does too.
 */
export function applyDocumentLanguage(locale: SupportedLocale): void {
  const root = globalThis.document?.documentElement;
  if (!root) return;
  root.lang = locale;
}

if ("window" in globalThis) {
  applyDocumentLanguage(parseStoredLocale(i18n.language) ?? "en");
  i18n.on("languageChanged", (lng: string) => {
    const safe = parseStoredLocale(lng) ?? ("en" as SupportedLocale);
    applyDocumentLanguage(safe);
    try {
      globalThis.localStorage.setItem(LOCALE_STORAGE_KEY, safe);
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
