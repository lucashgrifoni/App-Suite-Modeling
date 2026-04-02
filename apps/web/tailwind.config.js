/** @type {import('tailwindcss').Config} */
export default {
  // Alinha `dark:` com ThemeContext (`document.documentElement[data-theme="dark"]`).
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        display: ['"Outfit"', '"DM Sans"', "system-ui", "sans-serif"],
      },
      colors: {
        otm: {
          primary: {
            DEFAULT: "var(--otm-primary)",
            hover: "var(--otm-primary-hover)",
            active: "var(--otm-primary-active)",
            subtle: "var(--otm-primary-subtle)",
            muted: "var(--otm-primary-muted)",
          },
          accent: "var(--otm-accent)",
          mint: {
            300: "var(--otm-mint-300)",
            400: "var(--otm-mint-400)",
            500: "var(--otm-mint-500)",
          },
          surface: {
            base: "var(--otm-surface-base)",
            1: "var(--otm-surface-1)",
            2: "var(--otm-surface-2)",
            3: "var(--otm-surface-3)",
            glass: "var(--otm-surface-glass)",
          },
          border: {
            DEFAULT: "var(--otm-border)",
            strong: "var(--otm-border-strong)",
          },
          text: {
            DEFAULT: "var(--otm-text)",
            muted: "var(--otm-text-muted)",
            subtle: "var(--otm-text-subtle)",
          },
          success: "var(--otm-success)",
          warning: "var(--otm-warning)",
          danger: "var(--otm-danger)",
          info: "var(--otm-info)",
        },
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
      },
      borderRadius: {
        otm: "var(--otm-radius-lg)",
        "otm-sm": "var(--otm-radius-sm)",
        "otm-md": "var(--otm-radius-md)",
        "otm-xl": "var(--otm-radius-xl)",
      },
      boxShadow: {
        otm: "var(--otm-shadow-md)",
        "otm-sm": "var(--otm-shadow-sm)",
        "otm-lg": "var(--otm-shadow-lg)",
        "otm-glow": "var(--otm-shadow-glow)",
        "otm-ring": "0 0 0 3px var(--otm-ring)",
      },
      zIndex: {
        60: "60",
        70: "70",
      },
      transitionDuration: {
        otm: "220ms",
        "otm-slow": "320ms",
      },
      transitionTimingFunction: {
        otm: "cubic-bezier(0.22, 1, 0.36, 1)",
        "otm-out": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        "page-enter": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.65" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(86, 255, 149, 0.12)" },
          "50%": { boxShadow: "0 0 32px rgba(86, 255, 149, 0.2)" },
        },
      },
      animation: {
        "page-enter": "page-enter 0.45s cubic-bezier(0.22, 1, 0.36, 1) both",
        shimmer: "shimmer 1.2s ease-in-out infinite",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        glow: "glow 4s ease-in-out infinite",
      },
      backgroundImage: {
        "otm-gradient-accent": "var(--otm-gradient-accent)",
        "otm-gradient-shine": "var(--otm-gradient-shine)",
      },
    },
  },
  plugins: [],
};
