import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AnalysisResult } from "../types/api";
import type { OtmDocument } from "../types/document";
import { applyKnownComponentIdTypoFixes } from "../utils/documentNormalize";

const DOC_KEY = "otm.web.document";
const ANALYSIS_KEY = "otm.web.analysis";

/** Garante campos obrigatórios do contrato API para análises antigas em sessionStorage. */
function normalizeAnalysis(raw: unknown): AnalysisResult | null {
  if (!raw || typeof raw !== "object") return null;
  const a = raw as Partial<AnalysisResult>;
  if (typeof a.engine_version !== "string" || typeof a.document_title !== "string" || !a.summary) {
    return null;
  }
  return {
    ...(a as AnalysisResult),
    structural_findings: a.structural_findings ?? [],
    trust_boundary_findings: a.trust_boundary_findings ?? [],
    heuristic_threats: a.heuristic_threats ?? [],
  };
}

function normalizeDoc(raw: unknown): OtmDocument | null {
  if (!raw || typeof raw !== "object") return null;
  const d = raw as OtmDocument;
  if (!d.model || !d.metadata) return null;
  return applyKnownComponentIdTypoFixes({
    ...d,
    metadata: {
      ...d.metadata,
      tags: d.metadata.tags ?? [],
    },
    components: d.components ?? [],
    data_flows: d.data_flows ?? [],
    trust_boundaries: d.trust_boundaries ?? [],
    assets: d.assets ?? [],
    threats: d.threats ?? [],
    mitigations: d.mitigations ?? [],
    evidence_suggestions: d.evidence_suggestions ?? [],
  });
}

function persistDocument(doc: OtmDocument | null) {
  try {
    if (doc) sessionStorage.setItem(DOC_KEY, JSON.stringify(doc));
    else sessionStorage.removeItem(DOC_KEY);
  } catch {
    /* quota / private mode */
  }
}

function persistAnalysis(a: AnalysisResult | null) {
  try {
    if (a) sessionStorage.setItem(ANALYSIS_KEY, JSON.stringify(a));
    else sessionStorage.removeItem(ANALYSIS_KEY);
  } catch {
    /* ignore */
  }
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
      return s ? normalizeAnalysis(JSON.parse(s)) : null;
    } catch {
      return null;
    }
  });

  const setDocumentValue = useCallback((d: OtmDocument | null) => {
    const normalized = d ? normalizeDoc(d) : null;
    setDocument(normalized);
    persistDocument(normalized);
    if (!d) {
      setAnalysis(null);
      persistAnalysis(null);
    }
  }, []);

  const setAnalysisValue = useCallback((a: AnalysisResult | null) => {
    const n = a ? normalizeAnalysis(a) : null;
    setAnalysis(n);
    persistAnalysis(n);
  }, []);

  const reset = useCallback(() => {
    setDocument(null);
    setAnalysis(null);
    persistDocument(null);
    persistAnalysis(null);
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
