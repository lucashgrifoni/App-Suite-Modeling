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
        manualChunks: {
          three: ["three"],
          r3f: ["@react-three/fiber", "@react-three/drei"],
        },
      },
    },
  },
});
