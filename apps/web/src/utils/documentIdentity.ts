import type { OtmDocument } from "../types/document";

/**
 * Stable fingerprint of a document, used to decide whether a cached analysis
 * still belongs to the model currently in the session.
 *
 * This exists because an analysis is only meaningful next to the exact document
 * it was computed from. This is an evidence tool: the Markdown, JSON and premium
 * report it emits are what an auditor reads, so pairing a new model with a
 * previous model's threat list is a correctness bug, not a cosmetic one.
 *
 * Not a security primitive — it only has to change when the document changes, so
 * a fast non-cryptographic hash is the right tool. Collisions would show a stale
 * analysis, which is the same failure we already had; the mitigation is that the
 * hash covers the whole serialised document, not a subset of fields.
 */

/**
 * Ascending key order. `Object.entries` never yields the same key twice, so the
 * equal case cannot occur and the comparator needs no third outcome.
 */
function compareKeys(a: string, b: string): number {
  return a < b ? -1 : 1;
}

/** Serialise with deterministic key order so re-normalising a document is not a "change". */
function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const fields = Object.entries(value as Record<string, unknown>)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => compareKeys(a, b))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`)
    .join(",");
  return `{${fields}}`;
}

/** FNV-1a, 32-bit. Sync and cheap enough to run on every document change. */
function fnv1a(input: string): string {
  let hash = 0x811c9dc5;
  // `for…of` walks whole code points, so an astral character (emoji in a component
  // name) is folded in once instead of as two surrogate halves. For BMP-only text
  // this produces exactly the same digest as the previous code-unit loop.
  for (const char of input) {
    // A character produced by the string iterator is never empty; the `?? 0` only
    // satisfies the `number | undefined` signature of `codePointAt`.
    hash ^= char.codePointAt(0) ?? 0;
    // `Math.imul` keeps the multiply in 32-bit space; `>>> 0` forces unsigned.
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

export function hashDocument(doc: OtmDocument | null): string | null {
  if (!doc) return null;
  return fnv1a(stableStringify(doc));
}
