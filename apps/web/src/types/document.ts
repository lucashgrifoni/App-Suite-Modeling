/**
 * Forma JSON enviada à API (aliases do schema: `model`, `metadata`, etc.).
 * A UI só monta/edit estas estruturas; validação e motor ficam no backend.
 */

export interface OtmModelInfo {
  schema_version: string;
  system_type: string;
  industry_sector: string;
  /** Perfil do template (e.g. `internal_admin_portal`) — usado pelo assistente adaptativo. */
  template_semantic_profile?: string | null;
  methodology?:
    | "stride"
    | "linddun"
    | "nist_data_centric"
    | "octave_allegro"
    | "cia_die"
    | "pasta"
    | "plot4ai";
}

export interface OtmMetadata {
  title: string;
  summary?: string | null;
  owner?: string | null;
  document_version?: string | null;
  /** Inclui tags `wz:...` do assistente adaptativo. */
  tags?: string[];
}

export interface OtmComponent {
  id: string;
  name: string;
  kind: string;
  description?: string | null;
  technology?: string | null;
  responsibility?: string | null;
  asset_ids?: string[];
  in_trust_boundary?: string | null;
}

export interface OtmDataFlow {
  id: string;
  name?: string | null;
  from_component: string;
  to_component: string;
  encrypted?: boolean | null;
  protocol?: string | null;
}

export interface OtmTrustBoundary {
  id: string;
  name: string;
  inference_note?: string | null;
  user_validated?: boolean | null;
  member_component_ids?: string[];
  outside_component_ids?: string[];
  crossing_flow_ids?: string[];
}

export interface OtmAsset {
  id: string;
  name: string;
  asset_kind?: string;
  data_classification?: string | null;
  business_criticality?: string | null;
  sensitivity?: string | null;
  related_component_ids?: string[];
  related_data_flow_ids?: string[];
}

export type DeclaredThreat = {
  id: string;
  title: string;
  treatment_status?: string;
  treatment_notes?: string | null;
  assignee?: string | null;
  metadata?: Record<string, unknown>;
  [field: string]: unknown;
};
export function isDeclaredThreat(value: unknown): value is DeclaredThreat {
  if (
    !value ||
    typeof value !== "object" ||
    !("id" in value) ||
    typeof value.id !== "string" ||
    !("title" in value) ||
    typeof value.title !== "string"
  )
    return false;
  return (
    (!("treatment_status" in value) || typeof value.treatment_status === "string") &&
    (!("treatment_notes" in value) ||
      value.treatment_notes == null ||
      typeof value.treatment_notes === "string") &&
    (!("assignee" in value) || value.assignee == null || typeof value.assignee === "string")
  );
}

export interface OtmDocument {
  model: OtmModelInfo;
  metadata: OtmMetadata;
  components: OtmComponent[];
  data_flows: OtmDataFlow[];
  trust_boundaries: OtmTrustBoundary[];
  assets: OtmAsset[];
  threats: unknown[];
  mitigations: unknown[];
  evidence_suggestions: unknown[];
}

export const COMPONENT_KINDS = [
  { value: "process", label: "Processo" },
  { value: "datastore", label: "Armazém de dados" },
  { value: "external_entity", label: "Entidade externa" },
  { value: "user", label: "Utilizador" },
  { value: "gateway", label: "Gateway" },
  { value: "queue", label: "Fila" },
  { value: "other", label: "Outro" },
] as const;

export const SYSTEM_TYPES = [
  { value: "web_application", label: "Aplicação web" },
  { value: "api_backend", label: "API / backend" },
  { value: "mobile_application", label: "Mobile" },
  { value: "desktop", label: "Desktop" },
  { value: "batch_data_pipeline", label: "Pipeline de dados" },
  { value: "iot_system", label: "IoT" },
  { value: "hybrid", label: "Híbrido" },
  { value: "other", label: "Outro" },
] as const;
