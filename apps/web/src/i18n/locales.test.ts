/**
 * The pt-BR bundle had perfect key parity with English and still shipped English labels on
 * Portuguese screens, because the *values* had been copied rather than translated. The
 * result was single controls and single cards mixing the two languages: a card titled
 * "Trust boundaries" over the subtitle "Notas de inferência, fluxos que cruzam…", a
 * dropdown labelled "Categoria" whose first option was "Todas as categorias" followed by
 * seven English ones, and an engine card reading "Maturidade: Evolving".
 *
 * Key parity cannot catch that, so this file guards the values instead: every pt-BR string
 * that is byte-identical to its English counterpart must be listed below as a deliberate
 * choice. Anything else is an untranslated label and fails the build.
 */

import { describe, expect, it } from "vitest";
import en from "./locales/en.json";
import ptBR from "./locales/pt-BR.json";

type Bundle = Record<string, unknown>;

function flatten(bundle: Bundle, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(bundle)) {
    const path = `${prefix}${key}`;
    if (value && typeof value === "object") {
      Object.assign(out, flatten(value as Bundle, `${path}.`));
    } else {
      out[path] = String(value);
    }
  }
  return out;
}

/**
 * Strings that read the same in both languages on purpose: product and standards names
 * (STRIDE, PLOT4ai, Kubernetes, Terraform), format identifiers the user copies verbatim
 * (`document_json`, "Flowchart LR"), interpolation-only fragments, and loanwords the
 * Portuguese copy already uses elsewhere in the same screen ("Templates", "Diff", "Pack:").
 */
const INTENTIONALLY_IDENTICAL: ReadonlySet<string> = new Set([
  "artifactPdf.threatBullet",
  "diff.baseline",
  "diff.documentJson",
  "diff.revisionPlaceholder",
  "document.componentKinds.gateway",
  "document.systemTypes.api_backend",
  "document.systemTypes.desktop",
  "document.systemTypes.mobile_application",
  "export.artifactLangEn",
  "export.fmtBundle",
  "export.fmtMermaidHint",
  "import.explanationsCode",
  "import.kindKubernetes",
  "import.kindTerraform",
  "language.en",
  "language.ptBR",
  "methodologyMeta.stride.bestFor",
  "modelQuality.confHint",
  "modelQuality.fitNist",
  "modelQuality.fitPasta",
  "nav.diff",
  "nav.templates",
  "quickStart.templateTitle",
  "runEngine.optCia",
  "runEngine.optNist",
  "runEngine.optOctave",
  "runEngine.optPlot4ai",
  "runEngine.optStride",
  "templates.packBadge",
  "templates.title",
  "threatsCard.framework",
  "threatsCard.liScore",
  "threatsCard.stride",
  "wizard.id",
  "workflow.diff",
  "workflow.hintImport",
]);

const flatEn = flatten(en as Bundle);
const flatPt = flatten(ptBR as Bundle);

describe("locale bundles", () => {
  it("defines every English key in pt-BR", () => {
    const missing = Object.keys(flatEn).filter((k) => !(k in flatPt));
    expect(missing).toEqual([]);
  });

  it("defines no pt-BR key that English lacks", () => {
    const extra = Object.keys(flatPt).filter((k) => !(k in flatEn));
    expect(extra).toEqual([]);
  });

  it("leaves no user-visible label in English on the Portuguese UI", () => {
    const untranslated = Object.keys(flatEn).filter(
      (k) => flatPt[k] === flatEn[k] && !INTENTIONALLY_IDENTICAL.has(k),
    );
    expect(untranslated).toEqual([]);
  });

  it("keeps the intentional-duplicate list free of entries that are now translated", () => {
    // A stale allowlist quietly stops guarding the key it names.
    const stale = [...INTENTIONALLY_IDENTICAL].filter((k) => flatPt[k] !== flatEn[k]);
    expect(stale).toEqual([]);
  });

  it("keeps the same interpolation placeholders in both languages", () => {
    const placeholders = (s: string) => [...s.matchAll(/\{\{(\w+)}}/g)].map((m) => m[1]).sort();
    const drifted = Object.keys(flatEn).filter(
      (k) =>
        JSON.stringify(placeholders(flatEn[k])) !== JSON.stringify(placeholders(flatPt[k] ?? "")),
    );
    expect(drifted).toEqual([]);
  });
});
