import type { AnalysisResult } from "./api";
import type { OtmDocument } from "./document";

export interface AnalysisHistoryEntry {
  id: string;
  createdAt: number;
  /** Origem do snapshot */
  trigger: "analysis" | "export";
  title: string;
  systemType: string;
  maxScore: number | null;
  summaryLine: string;
  document: OtmDocument;
  analysis: AnalysisResult | null;
}
