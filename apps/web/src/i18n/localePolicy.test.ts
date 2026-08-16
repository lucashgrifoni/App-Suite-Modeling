import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getInitialLocaleFromWindow,
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

describe("getInitialLocaleFromWindow (English-first)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubWindow(stored: string | null): void {
    // Presence of `window` marks a browser env; localStorage lives on globalThis
    // (in a real browser `window === globalThis`), matching the production access.
    vi.stubGlobal("window", { localStorage: { getItem: (_k: string) => stored } });
    vi.stubGlobal("localStorage", { getItem: (_k: string) => stored });
  }

  it("abre em en por padrão quando não há preferência guardada", () => {
    stubWindow(null);
    expect(getInitialLocaleFromWindow()).toBe("en");
  });

  it("respeita a preferência guardada (pt-BR prevalece)", () => {
    stubWindow("pt-BR");
    expect(getInitialLocaleFromWindow()).toBe("pt-BR");
  });

  it("ignora preferência guardada inválida e cai em en", () => {
    stubWindow("fr");
    expect(getInitialLocaleFromWindow()).toBe("en");
  });

  it("retorna en em ambiente sem window (SSR/node)", () => {
    // sem stub de window: typeof window === "undefined" no ambiente node
    expect(getInitialLocaleFromWindow()).toBe("en");
  });
});

describe("storage the browser refuses", () => {
  // Safari em navegação privada, um perfil com cookies de terceiros bloqueados, ou uma política
  // corporativa: `localStorage.getItem` lança `SecurityError` em vez de devolver `null`. Este era
  // o **único** acesso a storage em `apps/web` sem `try` — e corre na inicialização do i18n, antes
  // de o React montar, por isso a app inteira ficava em branco. Sem mensagem, sem fallback.
  const denyStorage = () => {
    const throwing = {
      getItem() {
        throw new DOMException("The operation is insecure.", "SecurityError");
      },
      setItem() {
        throw new DOMException("The operation is insecure.", "SecurityError");
      },
      removeItem() {},
      clear() {},
      key: () => null,
      length: 0,
    } as unknown as Storage;
    vi.spyOn(globalThis, "localStorage", "get").mockReturnValue(throwing);
  };

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not throw when the browser denies storage", () => {
    denyStorage();

    expect(() => getInitialLocaleFromWindow()).not.toThrow();
  });

  it("falls back to the product's primary language", () => {
    denyStorage();

    expect(getInitialLocaleFromWindow()).toBe("en");
  });
});
