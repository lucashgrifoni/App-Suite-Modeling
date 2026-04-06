import { describe, expect, it } from "vitest";
import { localeFromUiLanguage, resolveExportArtifactLocale } from "./exportArtifactLocale";

describe("exportArtifactLocale", () => {
  it("localeFromUiLanguage maps pt variants to pt-BR", () => {
    expect(localeFromUiLanguage("pt-BR")).toBe("pt-BR");
    expect(localeFromUiLanguage("pt")).toBe("pt-BR");
    expect(localeFromUiLanguage("pt-PT")).toBe("pt-BR");
  });

  it("localeFromUiLanguage maps other UI codes to en", () => {
    expect(localeFromUiLanguage("en")).toBe("en");
    expect(localeFromUiLanguage("en-US")).toBe("en");
    expect(localeFromUiLanguage("fr")).toBe("en");
  });

  it("resolveExportArtifactLocale prefers explicit pt-BR or en", () => {
    expect(resolveExportArtifactLocale("pt-BR", "en")).toBe("pt-BR");
    expect(resolveExportArtifactLocale("en", "pt-BR")).toBe("en");
  });

  it("resolveExportArtifactLocale falls back to UI when ui or undefined", () => {
    expect(resolveExportArtifactLocale("ui", "pt-BR")).toBe("pt-BR");
    expect(resolveExportArtifactLocale(undefined, "en-US")).toBe("en");
  });
});
