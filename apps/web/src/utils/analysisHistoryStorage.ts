import type { AnalysisHistoryEntry } from "../types/analysisHistory";

// localStorage namespace for the analysis history list. Not a secret — it is
// a public identifier inside the browser's per-origin storage.
const STORAGE_NAMESPACE = "otm.analysis.history";
const MAX_ENTRIES = 20;

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

export function saveHistory(entries: AnalysisHistoryEntry[]): void {
  try {
    localStorage.setItem(STORAGE_NAMESPACE, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
  } catch {
    /* quota */
  }
}

export function pushHistoryEntry(entry: AnalysisHistoryEntry): void {
  const cur = loadHistory();
  const next = [entry, ...cur.filter((e) => e.id !== entry.id)].slice(0, MAX_ENTRIES);
  saveHistory(next);
}
