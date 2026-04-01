import type { AnalysisResult } from "./api";

export type MethodologyId = AnalysisResult["methodology"];

export type MethodologyMaturity = "Mature" | "Evolving" | "Specialized" | "Experimental";

export interface MethodologyMeta {
  hint: string;
  bestFor: string;
  maturity: MethodologyMaturity;
  category: string;
}

