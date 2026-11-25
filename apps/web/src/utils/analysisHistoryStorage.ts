import type { AnalysisHistoryEntry } from "../types/analysisHistory";

// localStorage namespace for the analysis history list. Not a secret — it is
// a public identifier inside the browser's per-origin storage.
export const STORAGE_NAMESPACE = "otm.analysis.history";
const MAX_ENTRIES = 20;

/**
 * What actually happened to a write.
 *
 * `evicted` — the newest snapshot was stored, but older ones had to go to make room.
 * `failed`  — not even the newest snapshot fits. It is gone; whatever was already stored
 *             is untouched.
 */
export type HistoryWriteOutcome = "ok" | "evicted" | "failed";

function isEntry(x: unknown): x is AnalysisHistoryEntry {
  if (!x || typeof x !== "object") return false;
  const o = x as Partial<AnalysisHistoryEntry>;
  if (typeof o.id !== "string" || typeof o.createdAt !== "number") return false;
  if (o.trigger !== "analysis" && o.trigger !== "export") return false;
  const d = o.document as { model?: unknown; metadata?: unknown } | undefined;
  if (!d?.model || !d?.metadata) return false;
  return true;
}

export function loadHistory(): AnalysisHistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_NAMESPACE);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isEntry);
  } catch {
    return [];
  }
}

/** One attempt at the whole list. `false` means the browser refused it (quota, private mode). */
function writeEntries(entries: readonly AnalysisHistoryEntry[]): boolean {
  try {
    localStorage.setItem(STORAGE_NAMESPACE, JSON.stringify(entries));
    return true;
  } catch {
    return false;
  }
}

function clearEntries(): void {
  try {
    localStorage.removeItem(STORAGE_NAMESPACE);
  } catch {
    /* private mode — there is nothing further to try */
  }
}

/**
 * Persist the list, shedding the OLDEST entries — never the newest — when the browser
 * refuses the write.
 *
 * localStorage has a per-origin quota that a handful of large models exhausts. Swallowing
 * the QuotaExceededError froze the stored list at whatever happened to fit first, so every
 * later snapshot was dropped while the UI still reported success: the entries a user cares
 * about most (the ones just produced) were exactly the ones discarded, and the "max 20"
 * the History page advertises became unreachable. Entries are newest-first, so retrying
 * without the tail sheds history in the order a user expects to lose it.
 */
export function saveHistory(entries: AnalysisHistoryEntry[]): HistoryWriteOutcome {
  const capped = entries.slice(0, MAX_ENTRIES);
  // The caller asked to store nothing — removing the last entry, say. That is a deliberate
  // clear, and the only reason to touch the key when there is nothing to write.
  if (capped.length === 0) {
    clearEntries();
    return "ok";
  }
  for (let size = capped.length; size > 0; size -= 1) {
    if (writeEntries(capped.slice(0, size))) {
      return size === capped.length ? "ok" : "evicted";
    }
  }
  // Not even the newest entry alone fits. The stored list is left exactly as it was: a
  // rejected `setItem` leaves the previous value intact in every browser, so what is on
  // disk is still valid and still fitted. Clearing it here would answer "this snapshot is
  // too big" by destroying every snapshot the user already had. Losing the new one is the
  // acceptable half of that trade, and `"failed"` lets the caller say so.
  return "failed";
}

export function pushHistoryEntry(entry: AnalysisHistoryEntry): HistoryWriteOutcome {
  const cur = loadHistory();
  const next = [entry, ...cur.filter((e) => e.id !== entry.id)].slice(0, MAX_ENTRIES);
  return saveHistory(next);
}

/**
 * Put back snapshots that a concurrent writer's copy of the list did not contain.
 *
 * localStorage offers no atomic read-modify-write. Two tabs that finish an analysis at the
 * same instant both read the list, both add their own entry to the copy they read, and both
 * write it back — so the second write erases the first tab's snapshot, with no error and no
 * sign on screen that anything was lost. Shrinking that window does not close it; the only
 * reliable signal is the `storage` event that tells the losing tab its entry is gone.
 *
 * Deliberately additive: entries already present are left exactly as they are, and the list
 * is re-sorted newest-first so a restored snapshot lands where the user expects it. Callers
 * decide *which* entries are eligible — see the provider, which offers only the ones this
 * tab wrote moments ago, so an entry the user deliberately deleted cannot come back.
 *
 * Returns `true` when the stored list actually had to be repaired.
 */
export function restoreMissingEntries(entries: readonly AnalysisHistoryEntry[]): boolean {
  if (entries.length === 0) return false;
  const stored = loadHistory();
  const present = new Set(stored.map((e) => e.id));
  const lost = entries.filter((e) => !present.has(e.id));
  if (lost.length === 0) return false;
  saveHistory([...lost, ...stored].sort((a, b) => b.createdAt - a.createdAt));
  return true;
}
