import { describe, expect, it } from "vitest";
import {
  LOCALE_STORAGE_KEY,
  parseStoredLocale,
  resolveInitialLocaleFromNavigator,
  SUPPORTED_LOCALES,
} from "./localePolicy";

describe("parseStoredLocale", () => {
  it("aceita apenas códigos da allowlist", () => {
    expect(parseStoredLocale("pt-BR")).toBe("pt-BR");
    expect(parseStoredLocale("en")).toBe("en");
    expect(parseStoredLocale("  en  ")).toBe("en");
  });

  it("rejeita locale arbitrário e valores inválidos", () => {
    expect(parseStoredLocale("fr")).toBeNull();
    expect(parseStoredLocale("<script>")).toBeNull();
    expect(parseStoredLocale("")).toBeNull();
    expect(parseStoredLocale(null)).toBeNull();
    expect(parseStoredLocale(undefined)).toBeNull();
    expect(parseStoredLocale("a".repeat(40))).toBeNull();
  });

  it("expor chave de storage estável", () => {
    expect(LOCALE_STORAGE_KEY).toBe("otm.web.locale");
    expect(SUPPORTED_LOCALES).toContain("pt-BR");
    expect(SUPPORTED_LOCALES).toContain("en");
  });
});

describe("resolveInitialLocaleFromNavigator", () => {
  it("mapeia variantes de português para pt-BR", () => {
    expect(resolveInitialLocaleFromNavigator(["pt-BR"])).toBe("pt-BR");
    expect(resolveInitialLocaleFromNavigator(["pt-PT"])).toBe("pt-BR");
    expect(resolveInitialLocaleFromNavigator(["pt"])).toBe("pt-BR");
  });

  it("usa en para não-português", () => {
    expect(resolveInitialLocaleFromNavigator(["en-US"])).toBe("en");
    expect(resolveInitialLocaleFromNavigator(["fr-FR"])).toBe("en");
    expect(resolveInitialLocaleFromNavigator([])).toBe("en");
  });
});
