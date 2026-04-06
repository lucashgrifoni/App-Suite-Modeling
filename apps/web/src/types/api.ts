/** Contratos alinhados à API FastAPI (`/v1`). Tipos parciais — o servidor é fonte de verdade. */

import type { OtmDocument } from "./document";

export interface TemplateListItem {
  id: string;
  title: string;
  description: string;
  suggested_pack: string | null;
  category: string;
  category_label: string;
  tags: string[];
  complexity: string | null;
  best_for: string | null;
  suggested_methodology: string | null;
  recommendation_hints: string[];
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
  target_asset_id?: string | null;
  risk: { likelihood: number; impact: number; score?: number | null };
  skipped_as_duplicate: boolean;
  framework_refs: FrameworkRef[];
  signal_refs?: string[];
  finding_family?: string | null;
  heuristic_tier?: string | null;
}

/** Alinhado a `StructuralFinding` no motor — achados de consistência estrutural. */
export interface StructuralFinding {
  code: string;
  severity: "info" | "warning";
  message: string;
}

/** Alinhado a `TrustBoundaryFinding` no motor. */
export interface TrustBoundaryFinding {
  code: string;
  message: string;
  data_flow_id?: string | null;
  from_boundary_id?: string | null;
  to_boundary_id?: string | null;
}

/** Entrada de audit trail do assistente (`wizard_signal_trace` no motor). */
export interface WizardSignalTraceEntry {
  source_tag: string;
  effect: "ranking_impact" | "corpus_mitigation" | "observation";
  weight: "low" | "moderate";
  impact_areas: string[];
  mechanism: "direct" | "contextual" | "auxiliary";
  explanation: string;
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

export interface QualityCheckItem {
  code: string;
  passed: boolean;
  message: string;
}

export interface ModelQualityPrecheck {
  score_0_100: number;
  band: "minimal" | "good" | "rich";
  methodology_fit: "strong" | "partial" | "weak";
  recommendation_confidence: "low" | "medium" | "high";
  methodology_fit_matrix: Record<string, string>;
  checks?: QualityCheckItem[];
}

export interface MethodologyCompletenessInfo {
  state: "complete" | "partial" | "degraded";
  reasons: string[];
  note?: string | null;
}

export interface AntiPatternHit {
  id: string;
  name: string;
  severity_hint: string;
  message: string;
  evidence: string[];
  expected_controls: string[];
  /** Alinhado ao motor (`AntiPatternHit.confidence_hint`). */
  confidence_hint?: string;
  detection_sources?: string[];
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
  structural_findings: StructuralFinding[];
  trust_boundary_findings: TrustBoundaryFinding[];
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
  model_quality_precheck?: ModelQualityPrecheck | null;
  methodology_completeness?: MethodologyCompletenessInfo | null;
  /** Notas quando tags `wz:` do assistente influenciam o motor. */
  wizard_context_notes?: string[];
  wizard_signal_trace?: WizardSignalTraceEntry[];
  anti_pattern_hits?: AntiPatternHit[];
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

/** Delta de uma heurística entre duas análises (`HeuristicThreatDelta` no motor). */
export interface HeuristicThreatDelta {
  threat_id: string;
  change: "added" | "removed" | "modified";
  match_kind?: "id" | "signature_remap";
  score_before?: number | null;
  score_after?: number | null;
  score_delta?: number | null;
  field_changes: FieldChange[];
  paired_id?: string | null;
}

export interface HeuristicThreatDeltaSection {
  added: HeuristicThreatDelta[];
  removed: HeuristicThreatDelta[];
  modified: HeuristicThreatDelta[];
}

export interface FrameworkRefCountDelta {
  catalog: string;
  count_before: number;
  count_after: number;
}

export interface PackHintsDelta {
  added: string[];
  removed: string[];
}

export interface MethodologyInsightsDelta {
  profile_before?: string | null;
  profile_after?: string | null;
  blocks_added: string[];
  blocks_removed: string[];
}

export interface TrustBoundaryFindingDelta {
  added_keys: string[];
  removed_keys: string[];
  count_before: number;
  count_after: number;
}

export interface StructuralFindingDelta {
  codes_added: string[];
  codes_removed: string[];
  count_before: number;
  count_after: number;
}

/**
 * Diff entre duas análises (`AnalysisDiff` no motor).
 * Presente em `ThreatModelComparisonResult.analysis` quando `run_analysis=true`.
 */
export interface AnalysisDiff {
  methodology_before: string;
  methodology_after: string;
  methodology_changed: boolean;
  max_risk_before?: number | null;
  max_risk_after?: number | null;
  max_risk_delta?: number | null;
  heuristic_threats: HeuristicThreatDeltaSection;
  framework_ref_counts: FrameworkRefCountDelta[];
  pack_control_hints: PackHintsDelta;
  methodology_insights?: MethodologyInsightsDelta | null;
  trust_boundary_findings?: TrustBoundaryFindingDelta | null;
  structural_findings?: StructuralFindingDelta | null;
  signature_remap_hints: string[];
}

export interface ThreatDeltaSummary {
  canonical: IdListSectionDiff;
  heuristic: HeuristicThreatDeltaSection;
}

/** Secções semânticas agregadas (heurística; não causalidade provada). */
export interface SemanticDiffSections {
  /** Contagens de IDs alterados (separado de interpretação). */
  structural_change_summary?: string[];
  improved: string[];
  worsened: string[];
  risk_impact: string[];
}

/**
 * Referência estável ligando mudança estrutural a notas de interpretação.
 * Espelha `semantic_structural_refs` em `ThreatModelComparisonResult.meta`.
 */
export interface SemanticStructuralRef {
  ref: string;
  entity_kind: string;
  entity_id: string;
  note: string;
}

/**
 * Metadados de comparação semântica — alinhados ao motor (`enrich_comparison_meta`).
 * Chaves extra podem existir; tipamos as estáveis para consumo na UI.
 */
export type ComparisonMeta = {
  semantic_insights?: string[];
  semantic_insights_version?: string;
  semantic_diff_sections?: SemanticDiffSections;
  /** Ligação explícita mudança estrutural → nota interpretativa (correlacional). */
  semantic_structural_refs?: SemanticStructuralRef[];
  /** Aviso único sobre limites inferenciais. */
  interpretation_disclaimer?: string;
} & Record<string, unknown>;

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
  analysis: AnalysisDiff | null;
  analysis_insights: string[];
  risk_delta: RiskDeltaSummary;
  threat_delta: ThreatDeltaSummary;
  recommendation_delta: RecommendationDelta;
  key_insights: string[];
  meta: ComparisonMeta;
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
