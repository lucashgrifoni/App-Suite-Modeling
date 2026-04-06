/**
 * Locale para artefactos gerados (PDF no cliente, Markdown via API).
 * Política: escolha explícita > idioma da UI > fallback en (via normalização do código UI).
 */

import { parseStoredLocale, type SupportedLocale } from "./localePolicy";

export type ExportArtifactLocale = SupportedLocale;

/**
 * Normaliza o idioma atual da UI para o par usado nos exportadores.
 */
export function localeFromUiLanguage(uiLanguage: string): ExportArtifactLocale {
  const exact = parseStoredLocale(uiLanguage);
  if (exact) return exact;
  const low = uiLanguage.trim().toLowerCase();
  if (low.startsWith("pt")) return "pt-BR";
  return "en";
}

/**
 * Resolve locale do artefacto: valor explícito (se definido) ou derivado da UI.
 */
export function resolveExportArtifactLocale(
  explicit: ExportArtifactLocale | "ui" | null | undefined,
  uiLanguage: string,
): ExportArtifactLocale {
  if (explicit === "pt-BR" || explicit === "en") return explicit;
  return localeFromUiLanguage(uiLanguage);
}
