/** Marketing copy — English for international visibility. */

export const hero = {
  tagline: "Threat modeling that engineers actually use.",
  subtitle:
    "An open-source platform for structured security analysis—methodology-native, automation-ready, and built for AppSec & DevSecOps workflows.",
};

export const about = {
  paragraphs: [
    "App Suite Modeling is a serious, extensible threat modeling workbench. It exists to bridge frameworks, teams, and delivery pipelines—so security design is continuous, explainable, and measurable.",
    "The project is open source and opinionated where it matters: STRIDE as a pragmatic default, with first-class pathways into LINDDUN, PASTA, PLOT4ai, and more. It unifies UI, CLI, and API so modeling fits how your org actually works.",
    "Whether you are threat-storming in a workshop or diffing models across releases, the same artifacts travel with you—backlog-aware, template-driven, and ready for AI-assisted reasoning.",
  ],
};

export const differentiators = [
  {
    title: "STRIDE-first",
    body: "A practical default taxonomy that stays fast in workshops and reviews.",
  },
  {
    title: "LINDDUN & privacy",
    body: "Privacy-by-design lenses without bolting on a separate workflow.",
  },
  {
    title: "PASTA",
    body: "Risk-centric thinking for process-oriented threat modeling.",
  },
  {
    title: "PLOT4ai",
    body: "AI/ML-specific threats with structured coverage and traceability.",
  },
  {
    title: "Real artifact imports",
    body: "Bring models from files and pipelines—ground analysis in what ships.",
  },
  {
    title: "Version diff",
    body: "See what changed between releases—signals, assumptions, and scope.",
  },
  {
    title: "Intelligent backlog",
    body: "Turn findings into actionable work with prioritization hooks.",
  },
  {
    title: "Explainability",
    body: "Make rationale legible for builders, auditors, and leadership.",
  },
  {
    title: "Templates & catalog",
    body: "Industry-grade starters that accelerate consistent modeling.",
  },
  {
    title: "AI system modeling",
    body: "Detects LLM, RAG, agent and inference components in your architecture and applies the PLOT4ai lens.",
  },
  {
    title: "Export & automation",
    body: "Fit the platform into CI/CD, docs portals, and compliance packs.",
  },
];

export type Maturity = "Core" | "Advanced" | "Experimental";

export const methodologies = [
  {
    id: "stride",
    name: "STRIDE",
    summary: "Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege.",
    when: "Baseline threat modeling for most systems and APIs.",
    maturity: "Core" as Maturity,
  },
  {
    id: "linddun",
    name: "LINDDUN",
    summary: "Privacy-focused threat elicitation with structured privacy categories.",
    when: "Data-heavy products, GDPR-style concerns, and user trust.",
    maturity: "Core" as Maturity,
  },
  {
    id: "nist",
    name: "NIST Data-Centric",
    summary: "Security guidance aligned to data-centric risk framing.",
    when: "Organizations standardizing on NIST-aligned security engineering.",
    maturity: "Advanced" as Maturity,
  },
  {
    id: "octave",
    name: "OCTAVE Allegro",
    summary: "Operational risk and asset-driven lightweight assessment patterns.",
    when: "Operational contexts with pragmatic, iterative assessments.",
    maturity: "Advanced" as Maturity,
  },
  {
    id: "cia",
    name: "CIA / CIA-DIE",
    summary: "Classic confidentiality, integrity, availability—extended where needed.",
    when: "Communicating impact in terms leadership already understands.",
    maturity: "Core" as Maturity,
  },
  {
    id: "pasta",
    name: "PASTA",
    summary: "Process for Attack Simulation and Threat Analysis—risk-centric stages.",
    when: "End-to-end risk narratives from business context to technical abuse cases.",
    maturity: "Advanced" as Maturity,
  },
  {
    id: "plot4ai",
    name: "PLOT4ai",
    summary: "AI/ML threat modeling with structured plotlines for ML systems.",
    when: "Models, pipelines, agents, and data flows around intelligent systems.",
    maturity: "Advanced" as Maturity,
  },
];

export const features = [
  {
    title: "Web UI",
    body: "Model, review, and collaborate with a focused interface for engineers.",
  },
  {
    title: "CLI",
    body: "Automate ingestion, transforms, and exports in developer workflows.",
  },
  {
    title: "API",
    body: "Integrate with portals, pipelines, and internal platforms cleanly.",
  },
  {
    title: "Templates",
    body: "Start from curated packs—cloud-native, SaaS, API backends, and more.",
  },
  {
    title: "Imports",
    body: "Bring real artifacts into analysis—less slideware, more signal.",
  },
  {
    title: "Diff",
    body: "Compare model versions to understand drift and regressions.",
  },
  {
    title: "Backlog",
    body: "Route threats into actionable tracking with clear ownership hooks.",
  },
  {
    title: "Explainability",
    body: "Preserve reasoning so reviews scale beyond a single expert.",
  },
  {
    title: "AI system modeling",
    body: "PLOT4ai heuristics for AI components, mapped to OWASP LLM Top 10 2025 and MITRE ATLAS.",
  },
];
