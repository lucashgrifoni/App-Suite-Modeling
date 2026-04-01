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
  appendSnapshot: (trigger: "analysis" | "export") => void;
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
    summaryLine: `${document.metadata.title} · L×I máx. ${maxScore ?? "—"}`,
    document: JSON.parse(JSON.stringify(document)) as OtmDocument,
    analysis: analysis ? (JSON.parse(JSON.stringify(analysis)) as AnalysisResult) : null,
  };
}

export function AnalysisHistoryProvider({ children }: Readonly<{ children: ReactNode }>) {
  const { document, analysis, setDocument, setAnalysis } = useSession();
  const [version, setVersion] = useState(0);

  const entries = useMemo(() => {
    void version;
    return loadHistory();
  }, [version]);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  const appendSnapshot = useCallback(
    (trigger: "analysis" | "export") => {
      if (!document) return;
      const entry = buildEntry(trigger, document, analysis);
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
