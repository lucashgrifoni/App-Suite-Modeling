/** Contratos alinhados à API FastAPI (`/v1`). Tipos parciais — o servidor é fonte de verdade. */

import type { OtmDocument } from "./document";

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

/** Contrato `ExplanationRecord` — explicabilidade estruturada (API/motor). */
export interface ExplanationRecord {
  id: string;
  type: string;
  category: string;
  subject: string;
  message: string;
  evidence: string[];
  confidence: "low" | "medium" | "high";
  related_entities: Array<{ entity_kind: string; entity_id: string }>;
  reasoning_path?: string[] | null;
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

export interface AiLayerAssessment {
  layer_id: string;
  label: string;
  status: "no_signal" | "weak" | "moderate" | "strong";
  evidence: string[];
}

export interface AiSystemContextSummary {
  schema_version: string;
  synopsis: string;
  pattern_tags: string[];
  layers: AiLayerAssessment[];
  primary_risk_surfaces: string[];
  prioritized_recommendations: string[];
  sensitive_data_notes: string[];
  heuristic_ids_by_layer: Record<string, string[]>;
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
  explanations?: ExplanationRecord[];
  ai_system_context?: AiSystemContextSummary | null;
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
  explanations?: ExplanationRecord[];
}

/** Resposta de `POST /v1/models/diff` — espelha `ThreatModelDiff` no core Python. */
export interface FieldChange {
  field: string;
  before?: unknown;
  after?: unknown;
}

export interface ModifiedEntity {
  id: string;
  changes: FieldChange[];
}

export interface IdListSectionDiff {
  added: string[];
  removed: string[];
  modified: ModifiedEntity[];
}

export interface ThreatModelDiff {
  baseline_title: string;
  revised_title: string;
  summary_line: string;
  model_info: FieldChange[];
  metadata: FieldChange[];
  business_context: FieldChange[];
  residual_risk_summary: FieldChange[];
  assets: IdListSectionDiff;
  components: IdListSectionDiff;
  data_flows: IdListSectionDiff;
  trust_boundaries: IdListSectionDiff;
  threats: IdListSectionDiff;
  mitigations: IdListSectionDiff;
  evidence_suggestions: IdListSectionDiff;
}

export interface DiffAggregateSection {
  added: string[];
  removed: string[];
  changed: string[];
}

export interface ComparisonSummary {
  headline: string;
  has_structural_changes: boolean;
  has_analysis_changes: boolean;
  methodology_in_model_changed: boolean;
}

export interface RiskDeltaSummary {
  analysis_max_score_baseline?: number | null;
  analysis_max_score_revised?: number | null;
  analysis_max_score_delta?: number | null;
  heuristic_increased_ids?: string[];
  heuristic_decreased_ids?: string[];
  document_residual_aggregate_changed?: boolean;
}

export interface RecommendationDelta {
  pack_hints_added?: string[];
  pack_hints_removed?: string[];
  framework_catalog_deltas?: Array<{
    catalog: string;
    count_before: number;
    count_after: number;
  }>;
  methodology_insight_blocks_added?: string[];
  methodology_insight_blocks_removed?: string[];
}

/** Resposta de `POST /v1/models/compare`. */
export interface ThreatModelComparisonResult {
  summary: ComparisonSummary;
  aggregate: {
    components: DiffAggregateSection;
    assets: DiffAggregateSection;
    data_flows: DiffAggregateSection;
    trust_boundaries: DiffAggregateSection;
    threats: DiffAggregateSection;
    mitigations: DiffAggregateSection;
    evidence_suggestions: DiffAggregateSection;
  };
  structural: ThreatModelDiff;
  structural_insights: string[];
  analysis: Record<string, unknown> | null;
  analysis_insights: string[];
  risk_delta: RiskDeltaSummary;
  threat_delta: Record<string, unknown>;
  recommendation_delta: RecommendationDelta;
  key_insights: string[];
  meta: Record<string, unknown>;
  explanations?: ExplanationRecord[];
}

export type ExportFormat =
  | "document_json"
  | "document_markdown"
  | "flowchart_mermaid"
  | "analysis_json"
  | "analysis_markdown"
  | "bundle_json";

export type ArtifactImportKind = "openapi" | "terraform" | "kubernetes";

export interface ArtifactInference {
  id: string;
  message: string;
  confidence: "low" | "medium" | "high";
  source: ArtifactImportKind | "helm";
  related_component_ids: string[];
}

export interface ArtifactImportResponse {
  document: OtmDocument;
  inferences: ArtifactInference[];
  unknowns: string[];
  assumptions: string[];
  explanations?: ExplanationRecord[];
}

export interface RemediationBacklogItem {
  id: string;
  title: string;
  description: string;
  rationale: string;
  priority_label: string;
  priority_explanation: string;
  effort_estimate: string;
  impact_estimate: string;
  quick_win: boolean;
  foundational: boolean;
  grouped_root_cause: string;
  suggested_control_type: string;
  explainability: string[];
  explanations?: ExplanationRecord[];
  next_step: string;
  recommended_owner: string | null;
}

export interface RemediationBacklogResponse {
  schema_version: string;
  document_title: string;
  methodology: string;
  executive_summary: string;
  synergy_notes: string[];
  items: RemediationBacklogItem[];
  by_root_cause: Record<string, string[]>;
  quick_win_ids: string[];
  foundational_ids: string[];
  high_impact_ids: string[];
  top_5_action_ids: string[];
}

export interface ApiErrorBody {
  code?: string;
  message?: string;
  errors?: unknown;
}
