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
import type { OtmDocument } from "../types/document";

const DOC_KEY = "otm.web.document";
const ANALYSIS_KEY = "otm.web.analysis";

function normalizeDoc(raw: unknown): OtmDocument | null {
  if (!raw || typeof raw !== "object") return null;
  const d = raw as OtmDocument;
  if (!d.model || !d.metadata) return null;
  return {
    ...d,
    components: d.components ?? [],
    data_flows: d.data_flows ?? [],
    trust_boundaries: d.trust_boundaries ?? [],
    assets: d.assets ?? [],
    threats: d.threats ?? [],
    mitigations: d.mitigations ?? [],
    evidence_suggestions: d.evidence_suggestions ?? [],
  };
}

interface SessionState {
  document: OtmDocument | null;
  analysis: AnalysisResult | null;
  setDocument: (d: OtmDocument | null) => void;
  setAnalysis: (a: AnalysisResult | null) => void;
  reset: () => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [document, setDocument] = useState<OtmDocument | null>(() => {
    try {
      const s = sessionStorage.getItem(DOC_KEY);
      return s ? normalizeDoc(JSON.parse(s)) : null;
    } catch {
      return null;
    }
  });
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(() => {
    try {
      const s = sessionStorage.getItem(ANALYSIS_KEY);
      return s ? (JSON.parse(s) as AnalysisResult) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (document) sessionStorage.setItem(DOC_KEY, JSON.stringify(document));
    else sessionStorage.removeItem(DOC_KEY);
  }, [document]);

  useEffect(() => {
    if (analysis) sessionStorage.setItem(ANALYSIS_KEY, JSON.stringify(analysis));
    else sessionStorage.removeItem(ANALYSIS_KEY);
  }, [analysis]);

  const setDocumentValue = useCallback((d: OtmDocument | null) => {
    setDocument(d ? normalizeDoc(d) : null);
    if (!d) setAnalysis(null);
  }, []);

  const setAnalysisValue = useCallback((a: AnalysisResult | null) => {
    setAnalysis(a);
  }, []);

  const reset = useCallback(() => {
    setDocument(null);
    setAnalysis(null);
    sessionStorage.removeItem(DOC_KEY);
    sessionStorage.removeItem(ANALYSIS_KEY);
  }, []);

  const value = useMemo(
    () => ({
      document,
      analysis,
      setDocument: setDocumentValue,
      setAnalysis: setAnalysisValue,
      reset,
    }),
    [document, analysis, setDocumentValue, setAnalysisValue, reset],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession outside SessionProvider");
  return ctx;
}
