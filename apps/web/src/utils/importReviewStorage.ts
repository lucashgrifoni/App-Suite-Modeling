import type { ArtifactInference, ExplanationRecord } from "../types/api";

/**
 * The inference / not-inferred review that an artifact import produces, kept next to the
 * draft it describes.
 *
 * The product makes reading this list the safety gate before the engine runs — "Import with
 * explicit inferences: review before running the engine", "Check the inference list before
 * going to analysis". It was held in plain component state while the draft it annotates went
 * to sessionStorage, so a refresh (or simply navigating away and back) left the user holding
 * a document whose stated review artifact had silently vanished, with no message and no way
 * to get it back short of re-importing — which now prompts to replace the model.
 *
 * Stored under the fingerprint of the document it was computed from, and only returned when
 * that fingerprint still matches. A review is a statement about one exact draft; showing it
 * beside a different model would be worse than showing nothing.
 */

const STORAGE_KEY = "otm.web.import.review";

export interface ImportReview {
  /** `hashDocument` of the draft this review describes. */
  documentKey: string;
  inferences: ArtifactInference[];
  unknowns: string[];
  explanations: ExplanationRecord[] | null;
}

function isRecordArray(value: unknown): boolean {
  return Array.isArray(value) && value.every((x) => typeof x === "object" && x !== null);
}

/** Shape check for a value that may have been written by an older build or hand-edited. */
function isReview(value: unknown): value is ImportReview {
  if (typeof value !== "object" || value === null) return false;
  const r = value as Partial<ImportReview>;
  if (typeof r.documentKey !== "string" || r.documentKey === "") return false;
  if (!isRecordArray(r.inferences)) return false;
  if (!Array.isArray(r.unknowns) || !r.unknowns.every((u) => typeof u === "string")) return false;
  if (r.explanations !== null && !isRecordArray(r.explanations)) return false;
  return true;
}

export function saveImportReview(review: ImportReview): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(review));
  } catch {
    /* quota / private mode — the panel is still on screen for this page load */
  }
}

/**
 * The stored review, or `null` when there is none, when it cannot be read, or when it
 * describes a different document than the one currently in the session.
 */
export function readImportReview(documentKey: string | null): ImportReview | null {
  if (documentKey === null) return null;
  let parsed: unknown;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isReview(parsed)) return null;
  return parsed.documentKey === documentKey ? parsed : null;
}

export function clearImportReview(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private mode */
  }
}
