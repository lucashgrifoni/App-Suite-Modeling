/**
 * Perguntas adaptativas por perfil semântico do template e foco por metodologia.
 * Valores persistem em `metadata.tags` como `wz:<perfil>:<id>=<yes|no|unk>` (sem lógica de negócio).
 */

import type { MethodologyId } from "../types/methodology";

export type AdaptiveAnswer = "yes" | "no" | "unk";

export interface AdaptivePrompt {
  id: string;
  label: string;
  hint?: string;
}

const PROFILE_INTERNAL_ADMIN = "internal_admin_portal";
const PROFILE_FILE = "file_handling_application";
const PROFILE_API = "api_backend_rest";
const PROFILE_ECOMMERCE = "industry_ecommerce";

const BY_PROFILE: Record<string, AdaptivePrompt[]> = {
  [PROFILE_INTERNAL_ADMIN]: [
    {
      id: "approval",
      label: "Existem ações privilegiadas que exigem aprovação explícita?",
      hint: "Segregação de funções e fluxos de aprovação.",
    },
    {
      id: "segregation",
      label: "Há segregação clara de funções entre admin e utilizadores finais?",
    },
    {
      id: "jit",
      label: "Existem privilégios just-in-time ou elevação temporária?",
    },
  ],
  [PROFILE_FILE]: [
    {
      id: "quarantine",
      label: "Há quarentena ou zona isolada antes do processamento?",
    },
    {
      id: "scan",
      label: "Antivírus, sandbox ou revalidação de conteúdo após upload?",
    },
    {
      id: "public_objects",
      label: "Objetos armazenados ficam expostos publicamente (URLs públicas)?",
    },
  ],
  [PROFILE_API]: [
    {
      id: "auth",
      label: "Autenticação e autorização estão explicitamente modeladas para clientes?",
    },
    {
      id: "rate_limit",
      label: "Há rate limiting / throttling aplicado?",
    },
    {
      id: "edge_controls",
      label: "Cache, WAF ou políticas fortes no perímetro (gateway) estão representados?",
    },
  ],
  [PROFILE_ECOMMERCE]: [
    {
      id: "checkout",
      label: "O fluxo de checkout e pagamento tem controlos contextuais claros?",
    },
    {
      id: "psp_boundary",
      label: "O processador de pagamentos (PSP) está como terceiro com boundary adequada?",
    },
    {
      id: "sensitive_data",
      label: "Dados sensíveis (conta, encomenda, pagamento) estão cobertos por ativos e classificação?",
    },
  ],
};

/** Texto curto por metodologia — disclosure, não validação no cliente. */
export function methodologyFocusHint(methodology: MethodologyId | undefined): string {
  switch (methodology) {
    case "stride":
      return "STRIDE: priorize componentes, fluxos, trust boundaries e ativos mínimos identificáveis.";
    case "pasta":
      return "PASTA: reforce objetivos de negócio, impacto, ativos e integrações críticas no texto do modelo.";
    case "nist_data_centric":
      return "NIST data-centric: classificação de dados, caminhos de dados e proteção em trânsito/repouso/uso.";
    default:
      return "Escolha a metodologia alinhada ao contexto; o motor avalia adequação no servidor.";
  }
}

export function promptsForProfile(templateSemanticProfile: string | undefined): AdaptivePrompt[] {
  if (!templateSemanticProfile) return [];
  const key = templateSemanticProfile.trim().toLowerCase();
  return BY_PROFILE[key] ?? [];
}

const TAG_PREFIX = "wz:";

export function parseAdaptiveTag(tag: string): { profile: string; id: string; answer: AdaptiveAnswer } | null {
  if (!tag.startsWith(TAG_PREFIX)) return null;
  const rest = tag.slice(TAG_PREFIX.length);
  const eq = rest.indexOf("=");
  if (eq <= 0) return null;
  const left = rest.slice(0, eq);
  const answer = rest.slice(eq + 1) as AdaptiveAnswer;
  const colon = left.indexOf(":");
  if (colon <= 0) return null;
  const profile = left.slice(0, colon);
  const id = left.slice(colon + 1);
  if (!profile || !id) return null;
  if (answer !== "yes" && answer !== "no" && answer !== "unk") return null;
  return { profile, id, answer };
}

export function setAdaptiveAnswer(
  tags: string[] | undefined,
  profile: string,
  promptId: string,
  answer: AdaptiveAnswer,
): string[] {
  const base = (tags ?? []).filter((t) => {
    const p = parseAdaptiveTag(t);
    return !(p?.profile === profile && p?.id === promptId);
  });
  if (answer === "unk") {
    return base;
  }
  base.push(`${TAG_PREFIX}${profile}:${promptId}=${answer}`);
  return base;
}

export function getAdaptiveAnswer(
  tags: string[] | undefined,
  profile: string,
  promptId: string,
): AdaptiveAnswer | null {
  for (const t of tags ?? []) {
    const p = parseAdaptiveTag(t);
    if (p?.profile === profile && p?.id === promptId) return p.answer;
  }
  return null;
}
