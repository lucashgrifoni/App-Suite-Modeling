/**
 * Política de locale: validação, persistência segura e resolução do idioma inicial.
 * Mantém a lista de idiomas permitidos como única fonte de verdade (anti-XSS / anti-injeção de locale).
 */

export const SUPPORTED_LOCALES = ["pt-BR", "en"] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_STORAGE_KEY = "otm.web.locale";

const LOCALE_SET = new Set<string>(SUPPORTED_LOCALES);

/**
 * Valida e normaliza um código de idioma vindo de storage, query ou eventos.
 * Rejeita valores arbitrários (não aceita paths, HTML ou códigos fora da allowlist).
 */
export function parseStoredLocale(raw: string | null | undefined): SupportedLocale | null {
  if (raw == null || typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed || trimmed.length > 32) return null;
  if (!LOCALE_SET.has(trimmed)) return null;
  return trimmed as SupportedLocale;
}

/**
 * Primeira carga sem preferência guardada: navigator.language / navigator.languages.
 * Regra: variantes de português → pt-BR; caso contrário → en (inclui ambíguo ou desconhecido).
 */
export function resolveInitialLocaleFromNavigator(languages: readonly string[]): SupportedLocale {
  for (const raw of languages) {
    if (!raw || typeof raw !== "string") continue;
    const lower = raw.trim().toLowerCase();
    if (lower.startsWith("pt")) return "pt-BR";
  }
  return "en";
}

/**
 * Idioma inicial no browser.
 *
 * Política do produto: **inglês é o idioma principal**. Na primeira carga, sem
 * preferência guardada, abrimos sempre em `en`. A escolha explícita do utilizador
 * é persistida em {@link LOCALE_STORAGE_KEY} e passa a prevalecer nas cargas
 * seguintes (incluindo pt-BR).
 *
 * A deteção por `navigator` ({@link resolveInitialLocaleFromNavigator}) deixou de
 * ditar o idioma inicial — continua exportada como utilitário reutilizável.
 */
export function getInitialLocaleFromWindow(): SupportedLocale {
  if ("window" in globalThis) {
    const stored = parseStoredLocale(globalThis.localStorage.getItem(LOCALE_STORAGE_KEY));
    if (stored) return stored;
  }
  return "en";
}
