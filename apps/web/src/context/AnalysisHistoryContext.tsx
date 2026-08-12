import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AnalysisResult } from "../types/api";
import type { AnalysisHistoryEntry } from "../types/analysisHistory";
import type { OtmDocument } from "../types/document";
import { loadHistory, pushHistoryEntry, saveHistory } from "../utils/analysisHistoryStorage";
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
   */
  appendSnapshot: (trigger: "analysis" | "export", analysis?: AnalysisResult | null) => void;
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

  const appendSnapshot = useCallback(
    (trigger: "analysis" | "export", snapshotAnalysis?: AnalysisResult | null) => {
      if (!document) return;
      const entry = buildEntry(
        trigger,
        document,
        snapshotAnalysis === undefined ? analysis : snapshotAnalysis,
      );
      pushHistoryEntry(entry);
      refresh();
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
