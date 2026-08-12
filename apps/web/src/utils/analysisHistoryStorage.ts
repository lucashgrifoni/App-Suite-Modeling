import type { AnalysisHistoryEntry } from "../types/analysisHistory";

// localStorage namespace for the analysis history list. Not a secret — it is
// a public identifier inside the browser's per-origin storage.
export const STORAGE_NAMESPACE = "otm.analysis.history";
const MAX_ENTRIES = 20;

/**
 * What actually happened to a write.
 *
 * `evicted` — the newest snapshot was stored, but older ones had to go to make room.
 * `failed`  — not even the newest snapshot fits, and nothing of it was stored.
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
  for (let size = capped.length; size > 0; size -= 1) {
    if (writeEntries(capped.slice(0, size))) {
      return size === capped.length ? "ok" : "evicted";
    }
  }
  // Either the caller asked to store nothing, or not one entry fits. Both end with an
  // empty key rather than a stale list that silently stopped at an arbitrary point.
  clearEntries();
  return capped.length === 0 ? "ok" : "failed";
}

export function pushHistoryEntry(entry: AnalysisHistoryEntry): HistoryWriteOutcome {
  const cur = loadHistory();
  const next = [entry, ...cur.filter((e) => e.id !== entry.id)].slice(0, MAX_ENTRIES);
  return saveHistory(next);
}
