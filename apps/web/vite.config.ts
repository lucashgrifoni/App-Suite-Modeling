import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

import { resolveApiProxyTarget } from "./src/config/devApiTarget.ts";

/**
 * CSP alinhada com `public/_headers` (deploy estático). Em dev não enviamos CSP no servidor
 * Vite para não quebrar HMR (`import.meta.hot` / WebSocket).
 */
const PREVIEW_SECURITY_HEADERS: Record<string, string> = {
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy":
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
};

const DEV_SECURITY_HEADERS: Record<string, string> = {
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy":
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
  "Cross-Origin-Opener-Policy": "same-origin",
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Sem isto, no Windows o Vite pode escutar só em IPv6 (::1); Chrome em
    // `localhost` usa 127.0.0.1 e devolve ERR_CONNECTION_REFUSED.
    host: true,
    headers: DEV_SECURITY_HEADERS,
    proxy: {
      "/api": {
        // Overridable via OTM_API_PORT / OTM_API_URL — see src/config/devApiTarget.ts.
        target: resolveApiProxyTarget(process.env),
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  preview: {
    headers: PREVIEW_SECURITY_HEADERS,
  },
});
