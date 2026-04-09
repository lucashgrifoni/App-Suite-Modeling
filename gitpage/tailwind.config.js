/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        midnight: "#0c124c",
        mist: "#d5d8dd",
        mint: "#08b98b",
        slate: "#5a6876",
        steel: "#7c8394",
        "surface-deep": "var(--semantic-surface-deep)",
        danger: {
          DEFAULT: "var(--semantic-danger)",
          strong: "var(--semantic-danger-strong)",
          muted: "var(--semantic-danger-muted)",
          text: "var(--semantic-danger-text)",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        display: ["Inter", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "grid-fade":
          "linear-gradient(to bottom, rgba(12,18,76,0) 0%, #0c124c 90%), linear-gradient(rgba(8,185,139,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(8,185,139,0.06) 1px, transparent 1px)",
        "radial-glow":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(8,185,139,0.35), transparent)",
        "mint-conic":
          "conic-gradient(from 180deg at 50% 50%, #08b98b 0deg, #0c124c 120deg, #5a6876 240deg, #08b98b 360deg)",
      },
      boxShadow: {
        mint: "0 0 40px rgba(8, 185, 139, 0.35)",
        card: "0 25px 50px -12px rgba(0, 0, 0, 0.45)",
        "hero-stack":
          "0 32px 64px -24px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(8, 185, 139, 0.12)",
        "hero-lip":
          "0 12px 28px -8px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
      },
      animation: {
        "pulse-slow": "pulse 5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        float: "float 6s ease-in-out infinite",
        "gradient-shift": "gradient 8s ease infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        gradient: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
    },
  },
  plugins: [],
};
