import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveEffectiveTheme, ThemeProvider, useTheme } from "./ThemeContext";

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
});

function wrapper({ children }: Readonly<{ children: ReactNode }>) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe("resolveEffectiveTheme", () => {
  it("returns explicit preferences directly", () => {
    expect(resolveEffectiveTheme("dark")).toBe("dark");
    expect(resolveEffectiveTheme("light")).toBe("light");
  });

  it("resolves 'system' from matchMedia", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({
      matches: true,
      media: q,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    expect(resolveEffectiveTheme("system")).toBe("light");
  });
});

describe("ThemeProvider / useTheme", () => {
  it("defaults to dark and reflects it on <html data-theme>", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.preference).toBe("dark");
    expect(result.current.effective).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("persists a changed preference to localStorage and updates the effective theme", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setPreference("light"));
    expect(result.current.preference).toBe("light");
    expect(result.current.effective).toBe("light");
    expect(localStorage.getItem("otm.web.themePreference")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("throws when used outside the provider", () => {
    expect(() => renderHook(() => useTheme())).toThrow(/ThemeProvider/);
  });
});
