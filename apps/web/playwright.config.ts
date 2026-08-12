import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    /* E2E fixtures assert PT-BR copy; pin locale so host browser language does not flip expected strings. */
    locale: "pt-BR",
    /*
     * Product policy is English-first: the app ignores navigator.language and reads the initial
     * locale only from localStorage (see src/i18n/localePolicy.ts:getInitialLocaleFromWindow).
     * Seed the stored preference so the PT-BR fixtures keep asserting the Portuguese journey.
     */
    storageState: {
      cookies: [],
      origins: [
        {
          origin: "http://127.0.0.1:4173",
          localStorage: [{ name: "otm.web.locale", value: "pt-BR" }],
        },
      ],
    },
  },
  webServer: {
    command: "node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    /*
     * Firefox uses a different engine (Gecko), so it catches what a Chromium-only suite
     * cannot: prefixed-CSS and layout differences, stricter parsing, and diverging
     * File/Blob and download behaviour on the export flow. Install it with
     * `node ./node_modules/@playwright/test/cli.js install firefox`.
     */
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
  ],
});
