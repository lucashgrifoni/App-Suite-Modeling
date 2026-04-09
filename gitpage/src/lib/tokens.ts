/** Design tokens — App Suite Modeling GitHub Page (locked palette). */
export const tokens = {
  midnight: "#0c124c",
  mist: "#d5d8dd",
  mint: "#08b98b",
  slate: "#5a6876",
  steel: "#7c8394",
} as const;

export type TokenKey = keyof typeof tokens;

/**
 * Semantic aliases (threat / status UI). Map to primitives where possible;
 * danger uses a calibrated red for dark surfaces (not in brand primaries).
 */
export const semantic = {
  success: tokens.mint,
  successMuted: "rgba(8, 185, 139, 0.14)",
  danger: "#f87171",
  dangerStrong: "#ef4444",
  dangerMuted: "rgba(248, 113, 113, 0.12)",
  dangerText: "#fecaca",
  surfaceDeep: "#0a0e38",
} as const;
