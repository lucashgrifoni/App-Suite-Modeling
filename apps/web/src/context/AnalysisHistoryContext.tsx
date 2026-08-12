import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AnalysisResult } from "../types/api";
import type { AnalysisHistoryEntry } from "../types/analysisHistory";
import type { OtmDocument } from "../types/document";
import {
  loadHistory,
  pushHistoryEntry,
  saveHistory,
  STORAGE_NAMESPACE,
  type HistoryWriteOutcome,
} from "../utils/analysisHistoryStorage";
import { useSession } from "./SessionContext";

interface AnalysisHistoryState {
  entries: AnalysisHistoryEntry[];
  refresh: () => void;
  /**
   * Append a snapshot of the current document.
   *
   * `analysis` is the analysis the snapshot is *of*. Callers that have just produced one
   * must pass it: a caller that does `setAnalysis(r)` and then `appendSnapshot(...)` in the
   * same event handler is still rendering with the pre-run session analysis, so leaving it
   * to be read from the session would store the previous run's result — or `null` on the
   * first run of a session. Callers that are only snapshotting what is already on screen
   * (the export page) can omit it and get the session analysis.
   *
   * Returns what became of the write so a caller announcing success can tell the truth:
   * `"failed"` means the browser's storage quota left no room and the snapshot is gone.
   */
  appendSnapshot: (
    trigger: "analysis" | "export",
    analysis?: AnalysisResult | null,
  ) => HistoryWriteOutcome;
  restore: (id: string) => void;
  remove: (id: string) => void;
}

const AnalysisHistoryContext = createContext<AnalysisHistoryState | null>(null);

function buildEntry(
  trigger: "analysis" | "export",
  document: OtmDocument,
  analysis: AnalysisResult | null,
): AnalysisHistoryEntry {
  const id = globalThis.crypto?.randomUUID?.() ?? `h_${Date.now()}`;
  const maxScore = analysis?.summary?.max_risk_score ?? null;
  return {
    id,
    createdAt: Date.now(),
    trigger,
    title: document.metadata.title,
    systemType: document.model.system_type,
    maxScore,
    document: structuredClone(document),
    analysis: analysis ? structuredClone(analysis) : null,
  };
}

export function AnalysisHistoryProvider({ children }: Readonly<{ children: ReactNode }>) {
  const { document, analysis, setDocument, setAnalysis } = useSession();
  const [entries, setEntries] = useState<AnalysisHistoryEntry[]>(() => loadHistory());

  const refresh = useCallback(() => setEntries(loadHistory()), []);

  // History lives in localStorage, which is shared by every tab on this origin. Reading it
  // once at mount meant a second tab kept rendering the list as it stood when that tab was
  // opened, with no hint it was stale — and a Remove click there acted on a list nobody was
  // looking at, making unrelated entries appear as the visible result of a delete.
  //
  // Two triggers, because neither covers the other: `storage` fires live while the tab is
  // running, and the visibility check catches up after a spell in the background, where a
  // browser is free to freeze the document and deliver it no events at all.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      // `key === null` is a whole-store clear, which also concerns us.
      if (e.key === null || e.key === STORAGE_NAMESPACE) refresh();
    };
    const onVisibility = () => {
      if (globalThis.document.visibilityState === "visible") refresh();
    };
    globalThis.addEventListener("storage", onStorage);
    globalThis.document.addEventListener("visibilitychange", onVisibility);
    return () => {
      globalThis.removeEventListener("storage", onStorage);
      globalThis.document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh]);

  const appendSnapshot = useCallback(
    (
      trigger: "analysis" | "export",
      snapshotAnalysis?: AnalysisResult | null,
    ): HistoryWriteOutcome => {
      // Nothing to snapshot. Not a storage failure, so callers must not warn about one.
      if (!document) return "ok";
      const entry = buildEntry(
        trigger,
        document,
        snapshotAnalysis === undefined ? analysis : snapshotAnalysis,
      );
      const outcome = pushHistoryEntry(entry);
      refresh();
      return outcome;
    },
    [document, analysis, refresh],
  );

  const restore = useCallback(
    (id: string) => {
      const e = loadHistory().find((x) => x.id === id);
      if (!e) return;
      setDocument(e.document);
      setAnalysis(e.analysis);
      refresh();
    },
    [setDocument, setAnalysis, refresh],
  );

  const remove = useCallback(
    (id: string) => {
      saveHistory(loadHistory().filter((e) => e.id !== id));
      refresh();
    },
    [refresh],
  );

  const value = useMemo(
    () => ({
      entries,
      refresh,
      appendSnapshot,
      restore,
      remove,
    }),
    [entries, refresh, appendSnapshot, restore, remove],
  );

  return (
    <AnalysisHistoryContext.Provider value={value}>{children}</AnalysisHistoryContext.Provider>
  );
}

export function useAnalysisHistory(): AnalysisHistoryState {
  const ctx = useContext(AnalysisHistoryContext);
  if (!ctx) throw new Error("useAnalysisHistory outside AnalysisHistoryProvider");
  return ctx;
}
