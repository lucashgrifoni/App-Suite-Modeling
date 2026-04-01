/**
 * Design tokens semânticos (espelho das variáveis CSS em index.css).
 * Use para lógica TS (ex.: charts) ou documentação; preferir classes Tailwind nas UI.
 */
export const otmBrand = {
  primary: "#30B27F",
  mint400: "#6AE899",
  accent: "#56FF95",
  mint300: "#7DFABE",
  mint500: "#76DB9B",
} as const;

export const motion = {
  durationFast: "150ms",
  duration: "220ms",
  durationSlow: "320ms",
  easing: "cubic-bezier(0.22, 1, 0.36, 1)",
  easingOut: "cubic-bezier(0.16, 1, 0.3, 1)",
} as const;

export const zIndex = {
  base: 0,
  dropdown: 40,
  sticky: 50,
  modal: 100,
  toast: 200,
} as const;
