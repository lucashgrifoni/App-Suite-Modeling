import type { MethodologyId, MethodologyMeta } from "../types/methodology";

export const METHODOLOGY_META: Record<MethodologyId, MethodologyMeta> = {
  stride: {
    hint: "Default técnico e mais maduro para web/API/cloud.",
    bestFor: "Web, API, cloud-native",
    maturity: "Mature",
    category: "General security",
  },
  linddun: {
    hint: "Privacidade: PII, consentimento, minimização e conformidade.",
    bestFor: "LGPD/GDPR e dados pessoais",
    maturity: "Evolving",
    category: "Privacy",
  },
  nist_data_centric: {
    hint: "Proteção de dados críticos e caminhos sensíveis.",
    bestFor: "Dados críticos/classificados",
    maturity: "Evolving",
    category: "Data-centric",
  },
  octave_allegro: {
    hint: "Risco de negócio orientado a ativos.",
    bestFor: "Ativos e risco organizacional",
    maturity: "Evolving",
    category: "Business risk",
  },
  cia_die: {
    hint: "Análise rápida e comunicação executiva.",
    bestFor: "Workshops rápidos",
    maturity: "Evolving",
    category: "Executive",
  },
  pasta: {
    hint: "Análise avançada risk-centric (ataque, vulnerabilidade, impacto).",
    bestFor: "Contextos enterprise avançados",
    maturity: "Specialized",
    category: "Advanced risk",
  },
  plot4ai: {
    hint: "Ameaças de IA/LLM (prompt, RAG, agentes, inferência).",
    bestFor: "Sistemas AI/LLM",
    maturity: "Specialized",
    category: "AI/LLM",
  },
};

