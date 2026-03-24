import { apiFetch } from "./client";
import type {
  AnalysisResult,
  ExportFormat,
  MethodologyRecommendation,
  TemplateListItem,
  ValidateResponse,
} from "../types/api";
import type { OtmDocument } from "../types/document";

export async function health(): Promise<{ status: string }> {
  return apiFetch("/health");
}

export async function createBlankModel(): Promise<{ document: OtmDocument }> {
  return apiFetch("/v1/models", { method: "POST" });
}

export async function listTemplates(): Promise<TemplateListItem[]> {
  return apiFetch("/v1/templates");
}

export async function instantiateTemplate(
  templateId: string,
): Promise<{ document: OtmDocument }> {
  return apiFetch(`/v1/templates/${encodeURIComponent(templateId)}/instantiate`, {
    method: "POST",
  });
}

export async function validateDocument(
  document: OtmDocument,
): Promise<ValidateResponse> {
  return apiFetch("/v1/models/validate", {
    method: "POST",
    json: { document },
  });
}

export async function analyzeDocument(
  document: OtmDocument,
  options?: {
    packId?: string | null;
    methodology?:
      | "stride"
      | "linddun"
      | "nist_data_centric"
      | "octave_allegro"
      | "cia_die"
      | "pasta"
      | "plot4ai"
      | null;
    autoRecommendMethodology?: boolean;
  },
): Promise<AnalysisResult> {
  return apiFetch("/v1/models/analyze", {
    method: "POST",
    json: {
      document,
      pack_id: options?.packId || null,
      methodology: options?.methodology ?? null,
      auto_recommend_methodology: options?.autoRecommendMethodology ?? false,
    },
  });
}

export async function recommendMethodology(
  document: OtmDocument,
): Promise<MethodologyRecommendation> {
  return apiFetch("/v1/models/recommend-methodology", {
    method: "POST",
    json: { document },
  });
}

export async function exportArtifacts(body: {
  document: OtmDocument;
  formats: ExportFormat[];
  pack_id?: string | null;
  analysis?: AnalysisResult | null;
}): Promise<{ artifacts: Record<string, string> }> {
  return apiFetch("/v1/exports", {
    method: "POST",
    json: {
      document: body.document,
      formats: body.formats,
      pack_id: body.pack_id ?? null,
      analysis: body.analysis ?? null,
    },
  });
}
