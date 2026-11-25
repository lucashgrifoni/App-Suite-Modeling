import {
  apiErrorFromResponseText,
  ApiMalformedResponseError,
  apiFetch,
  fetchWithTimeout,
  REPORT_TIMEOUT_MS,
} from "./client";
import type {
  AnalysisResult,
  ArtifactImportKind,
  ArtifactImportResponse,
  ExportFormat,
  MethodologyRecommendation,
  OpenApiReimportPreview,
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

export type TemplateListQuery = {
  category?: string;
  tag?: string;
  complexity?: string;
  q?: string;
};

export async function listTemplates(params?: TemplateListQuery): Promise<TemplateListItem[]> {
  const sp = new URLSearchParams();
  if (params?.category) sp.set("category", params.category);
  if (params?.tag) sp.set("tag", params.tag);
  if (params?.complexity) sp.set("complexity", params.complexity);
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  const suffix = qs ? `?${qs}` : "";
  return apiFetch(`/v1/templates${suffix}`);
}

export async function getTemplate(templateId: string): Promise<TemplateListItem> {
  return apiFetch(`/v1/templates/${encodeURIComponent(templateId)}`);
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
  /** pt-BR | en — textos user-facing em Markdown; omitido = política do servidor (pt-BR). */
  locale?: string | null;
}): Promise<{ artifacts: Record<string, string> }> {
  return apiFetch("/v1/exports", {
    method: "POST",
    json: {
      document: body.document,
      formats: body.formats,
      pack_id: body.pack_id ?? null,
      analysis: body.analysis ?? null,
      locale: body.locale ?? null,
    },
  });
}

const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? "/api";

export type RiskReportFormat = "markdown" | "pdf";

export async function fetchRiskReport(args: {
  document: OtmDocument;
  analysis: AnalysisResult | null;
  outputFormat: RiskReportFormat;
  locale: "pt-BR" | "en";
  snapshotDate?: number;
}): Promise<{ blob: Blob; filename: string }> {
  const res = await fetchWithTimeout(
    `${API_PREFIX}/v1/reports`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document: args.document,
        analysis: args.analysis,
        run_analysis: args.analysis === null,
        output_format: args.outputFormat,
        locale: args.locale,
      }),
    },
    REPORT_TIMEOUT_MS,
  );
  if (!res.ok) {
    throw apiErrorFromResponseText(res.status, res.statusText, await res.text());
  }
  const pdf = args.outputFormat === "pdf";
  const mediaType = pdf ? "application/pdf" : "text/markdown";
  if (res.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== mediaType) {
    throw new ApiMalformedResponseError(res.status);
  }
  const safeTitle = args.document.metadata.title.replaceAll(/[^\w-]+/g, "_").slice(0, 60) || "model";
  const revision = args.snapshotDate ? `-${args.snapshotDate}` : "";
  return {
    blob: await res.blob(),
    filename: `otm-report-${safeTitle}${revision}.${pdf ? "pdf" : "md"}`,
  };
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

export async function previewOpenApiReimport(
  previous: File,
  revised: File,
  document: OtmDocument,
): Promise<OpenApiReimportPreview> {
  const body = new FormData();
  body.append("previous", previous);
  body.append("revised", revised);
  body.append("document", new Blob([JSON.stringify(document)], { type: "application/json" }), "model.json");
  return apiFetch("/v1/imports/openapi/reimport-preview", { method: "POST", body });
}
