/**
 * Contratos da API `/v1` alinhados ao OpenAPI gerado a partir do FastAPI.
 *
 * Tipos de motor (`AnalysisResult`, `ThreatModelComparisonResult`, …) vêm de
 * `./generated/openapi` (regenerar: `npm run contracts:sync` na pasta `apps/web`).
 * `ThreatModelComparisonResult.meta` corresponde a `ComparisonResultMeta` no OpenAPI;
 * esta interseção (`ComparisonMeta`) documenta campos semânticos estáveis para o SPA.
 */

import type { components } from "./generated/openapi";

type Schemas = components["schemas"];

export type TemplateListItem = Schemas["TemplateListItem"];
export type ValidateResponse = Schemas["ValidateResponse"];
export type FrameworkRef = Schemas["FrameworkRef"];
export type ExplanationRecord = Schemas["ExplanationRecord"];
export type HeuristicThreat = Schemas["HeuristicThreat"];
export type StructuralFinding = Schemas["StructuralFinding"];
export type TrustBoundaryFinding = Schemas["TrustBoundaryFinding"];
export type WizardSignalTraceEntry = Schemas["WizardSignalTraceEntry"];
export type AnalysisSummary = Schemas["AnalysisSummary"];
export type AiLayerAssessment = Schemas["AiLayerAssessment"];
export type AiSystemContextSummary = Schemas["AiSystemContextSummary"];
export type QualityCheckItem = Schemas["QualityCheckItem"];
export type ModelQualityPrecheck = Schemas["ModelQualityPrecheck"];
export type MethodologyCompletenessInfo = Schemas["MethodologyCompletenessInfo"];
export type AntiPatternHit = Schemas["AntiPatternHit"];
/** Resposta real de `/analyze`: listas e summary sempre presentes após serialização. */
export type AnalysisResult = Schemas["AnalysisResult"] & {
  summary: Schemas["AnalysisSummary"];
  heuristic_threats: Schemas["HeuristicThreat"][];
  structural_findings: Schemas["StructuralFinding"][];
  trust_boundary_findings: Schemas["TrustBoundaryFinding"][];
};
export type MethodologyRecommendation = Schemas["RecommendMethodologyResponse"];
export type FieldChange = Schemas["FieldChange"];
export type ModifiedEntity = Schemas["ModifiedEntity"];
export type IdListSectionDiff = Schemas["IdListSectionDiff"];
export type ThreatModelDiff = Schemas["ThreatModelDiff"];
/** Secção added/removed/changed dentro de `aggregate` (UI diff). */
export interface DiffAggregateSection {
  added?: string[];
  removed?: string[];
  changed?: string[];
}
export type ComparisonSummary = Schemas["ComparisonSummary"];
export type RiskDeltaSummary = Schemas["RiskDeltaSummary"];
export type RecommendationDelta = Schemas["RecommendationDelta"];
export type HeuristicThreatDelta = Schemas["HeuristicThreatDelta"];
export type HeuristicThreatDeltaSection = Schemas["HeuristicThreatDeltaSection"];
export type FrameworkRefCountDelta = Schemas["FrameworkRefCountDelta"];
export type PackHintsDelta = Schemas["PackHintsDelta"];
export type MethodologyInsightsDelta = Schemas["MethodologyInsightsDelta"];
export type TrustBoundaryFindingDelta = Schemas["TrustBoundaryFindingDelta"];
export type StructuralFindingDelta = Schemas["StructuralFindingDelta"];
export type AnalysisDiff = Schemas["AnalysisDiff"];
export type ThreatDeltaSummary = Schemas["ThreatDeltaSummary"];
export type ExportFormat = Schemas["ExportFormat"];
export type ArtifactImportKind = Schemas["InferenceRecordBody"]["source"];
export type ArtifactInference = Schemas["InferenceRecordBody"];
export type ArtifactImportResponse = Schemas["ArtifactImportResponse"];
export type OpenApiReimportPreview = Schemas["OpenApiReimportPreview"];

/** Secções semânticas agregadas (heurística; não causalidade provada). */
export interface SemanticDiffSections {
  structural_change_summary?: string[];
  improved: string[];
  worsened: string[];
  risk_impact: string[];
}

/** Referência estável: mudança estrutural ↔ nota interpretativa. */
export interface SemanticStructuralRef {
  ref: string;
  entity_kind: string;
  entity_id: string;
  note: string;
  /** Derivado do prefixo da ref (ex. trust_boundary_added). */
  change_category?: string | null;
}

/**
 * Ligação explícita entre ref estrutural e secção interpretativa (v1.5).
 * Inclui `anchoring_rationale`; `medium` só com ≥2 tokens lexicais.
 */
export interface SemanticInterpretationLink {
  structural_ref: string;
  related_section: "insights" | "improved" | "worsened" | "risk_impact";
  summary: string;
  link_kind?: "lexical_token_overlap" | "entity_topic_correlation";
  inference_strength?: "low" | "medium";
  anchoring_rationale?: string;
  shared_tokens?: string[];
  entity_kind?: string | null;
}

/**
 * Metadados de comparação semântica — chaves estáveis documentadas no motor.
 * OpenAPI: `ComparisonResultMeta` com raiz fechada e `extensions` para evolução.
 */
export type ComparisonMeta = NonNullable<Schemas["ThreatModelComparisonResult"]["meta"]> & {
  semantic_insights?: string[];
  semantic_insights_version?: string;
  semantic_diff_sections?: SemanticDiffSections;
  semantic_structural_refs?: SemanticStructuralRef[];
  semantic_interpretation_links?: SemanticInterpretationLink[];
  interpretation_disclaimer?: string;
  comparison_contract_version?: string;
  extensions?: Record<string, unknown>;
};

/** Resposta de `/compare` com campos que a API preenche de forma estável. */
export type ThreatModelComparisonResult = Schemas["ThreatModelComparisonResult"] & {
  risk_delta: Schemas["RiskDeltaSummary"];
  threat_delta: Schemas["ThreatDeltaSummary"];
  key_insights: string[];
  meta: ComparisonMeta;
};

/** Resposta JSON do backlog — ainda não exposta como `response_model` na API. */
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

export type { OtmDocument } from "./document";
