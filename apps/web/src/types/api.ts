/** Contratos alinhados à API FastAPI (`/v1`). Tipos parciais — o servidor é fonte de verdade. */

export interface TemplateListItem {
  id: string;
  title: string;
  description: string;
  suggested_pack: string | null;
}

export interface ValidateResponse {
  valid: true;
  title: string;
  schema_version: string;
  component_count: number;
  threat_count: number;
}

export interface FrameworkRef {
  framework: string;
  control_id: string;
  notes?: string | null;
}

export interface HeuristicThreat {
  id: string;
  title: string;
  description: string;
  stride: string;
  target_component_id?: string | null;
  target_data_flow_id?: string | null;
  risk: { likelihood: number; impact: number; score?: number | null };
  skipped_as_duplicate: boolean;
  framework_refs: FrameworkRef[];
}

export interface AnalysisSummary {
  structural_findings: number;
  trust_boundary_findings: number;
  heuristic_threats_generated: number;
  heuristic_threats_skipped_duplicate: number;
  pack_threats_generated: number;
  pack_threats_skipped_duplicate: number;
  max_risk_score: number | null;
  framework_ref_counts_by_catalog: Record<string, number>;
}

export interface AnalysisResult {
  engine_version: string;
  methodology:
    | "stride"
    | "linddun"
    | "nist_data_centric"
    | "octave_allegro"
    | "cia_die"
    | "pasta"
    | "plot4ai";
  methodology_recommendation_reason?: string | null;
  document_title: string;
  heuristic_threats: HeuristicThreat[];
  summary: AnalysisSummary;
  methodology_insights?: {
    profile?: string | null;
    blocks: Array<{ key: string; title: string; items: string[] }>;
  } | null;
  industry_pack_id: string | null;
  pack_control_hints: string[];
}

export interface MethodologyRecommendation {
  methodology:
    | "stride"
    | "linddun"
    | "nist_data_centric"
    | "octave_allegro"
    | "cia_die"
    | "pasta"
    | "plot4ai";
  reason: string;
}

export type ExportFormat =
  | "document_json"
  | "document_markdown"
  | "flowchart_mermaid"
  | "analysis_json"
  | "analysis_markdown"
  | "bundle_json";

export interface ApiErrorBody {
  code?: string;
  message?: string;
  errors?: unknown;
}
