import "@testing-library/jest-dom/vitest";
// Initialise i18next once so components using `useTranslation` / the `i18n`
// singleton render real strings instead of throwing.
import "../i18n/i18n";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom does not implement matchMedia; ThemeContext and usePrefersReducedMotion
// rely on it. Default to "no match" (dark theme / no reduced motion); individual
// tests can stub a different value via vi.stubGlobal("matchMedia", ...).
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string): MediaQueryList =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList,
  });
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
