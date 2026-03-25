import { apiFetch } from "./client";
import type {
  AnalysisResult,
  ArtifactImportKind,
  ArtifactImportResponse,
  ExportFormat,
  MethodologyRecommendation,
  RemediationBacklogResponse,
  TemplateListItem,
  ThreatModelComparisonResult,
  ThreatModelDiff,
  ValidateResponse,
} from "../types/api";
import type { OtmDocument } from "../types/document";
import type { MethodologyId } from "../types/methodology";

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

export async function diffDocuments(
  baseline: OtmDocument,
  revised: OtmDocument,
): Promise<ThreatModelDiff> {
  return apiFetch("/v1/models/diff", {
    method: "POST",
    json: {
      baseline,
      revised,
    },
  });
}

export async function compareThreatModels(
  baseline: OtmDocument,
  revised: OtmDocument,
  options?: {
    runAnalysis?: boolean;
    packId?: string | null;
    baselineAnalysis?: AnalysisResult | null;
    revisedAnalysis?: AnalysisResult | null;
  },
): Promise<ThreatModelComparisonResult> {
  return apiFetch("/v1/models/compare", {
    method: "POST",
    json: {
      baseline,
      revised,
      run_analysis: options?.runAnalysis ?? false,
      pack_id: options?.packId ?? null,
      baseline_analysis: options?.baselineAnalysis ?? null,
      revised_analysis: options?.revisedAnalysis ?? null,
    },
  });
}

export async function analyzeDocument(
  document: OtmDocument,
  options?: {
    packId?: string | null;
    methodology?: MethodologyId | null;
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

export async function fetchRemediationBacklog(args: {
  document: OtmDocument;
  analysis: AnalysisResult;
}): Promise<RemediationBacklogResponse> {
  return apiFetch("/v1/remediation/backlog", {
    method: "POST",
    json: {
      document: args.document,
      analysis: args.analysis,
      run_analysis: false,
    },
  });
}

export async function importArtifact(
  kind: ArtifactImportKind,
  file: File,
): Promise<ArtifactImportResponse> {
  const fd = new FormData();
  fd.append("file", file);
  return apiFetch(`/v1/imports/${encodeURIComponent(kind)}`, {
    method: "POST",
    body: fd,
  });
}
