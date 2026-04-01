/** Design tokens — App Suite Modeling GitHub Page (locked palette). */
export const tokens = {
  midnight: "#0c124c",
  mist: "#d5d8dd",
  mint: "#08b98b",
  slate: "#5a6876",
  steel: "#7c8394",
} as const;

export type TokenKey = keyof typeof tokens;
