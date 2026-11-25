import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { resolveApiPort } from "./src/config/devApiTarget";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");

/**
 * Port 8000 is heavily contended on developer machines; when it is taken,
 * uvicorn dies with an opaque bind error and the whole no-mock E2E run is
 * unrunnable. Set `OTM_API_PORT` to move both uvicorn and the Vite proxy
 * together — they must never disagree.
 */
const apiPort = resolveApiPort(process.env);

/**
 * E2E híbrido: Vite (proxy /api → backend) + uvicorn real na porta 8000.
 * Requer `pip install -e ".[api]"` e dependências do motor no PATH do Python.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /hybrid\.spec\.ts/,
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    /* Match the standard config: PT-BR copy is asserted, but the app is English-first and reads
       the initial locale only from localStorage (src/i18n/localePolicy.ts). Pin locale + seed it. */
    locale: "pt-BR",
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
  webServer: [
    {
      command: `python -m uvicorn otm_api.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: repoRoot,
      url: `http://127.0.0.1:${apiPort}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: {
        OTM_RATE_LIMIT_DISABLED: "1",
      },
    },
    {
      command: "node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4173",
      cwd: __dirname,
      url: "http://127.0.0.1:4173",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      // Keeps the Vite `/api` proxy pointed at the same port uvicorn just bound.
      env: {
        OTM_API_PORT: apiPort,
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    /* Same rationale as playwright.config.ts: a second engine against the REAL backend. */
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
  ],
});
