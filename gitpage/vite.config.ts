import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Base `./` keeps asset URLs relative so the site works on GitHub Project Pages
 * (any repository path) without hardcoding the repo slug.
 */
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // Vite 8 / Rolldown: manualChunks deve ser função (objeto legado rejeitado).
        manualChunks(id: string) {
          if (id.includes("/node_modules/three/")) return "three";
          if (
            id.includes("/node_modules/@react-three/fiber/") ||
            id.includes("/node_modules/@react-three/drei/")
          ) {
            return "r3f";
          }
        },
      },
    },
  },
});
