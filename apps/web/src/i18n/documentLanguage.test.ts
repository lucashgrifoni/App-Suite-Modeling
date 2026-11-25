/**
 * `index.html` ships a static `<html lang="en">` and nothing in `src/` ever wrote the
 * attribute, so choosing PT-BR rendered the whole interface in Portuguese while the document
 * still declared itself English — across reloads, since only the locale preference was
 * persisted. That is a WCAG 2.2 SC 3.1.1 (Language of Page, Level A) failure: a screen
 * reader picks pronunciation from `lang` and reads the Portuguese copy with an English
 * voice. The theme already syncs `documentElement.dataset.theme`; the language did not.
 */

import { afterEach, describe, expect, it } from "vitest";
import i18n, { applyDocumentLanguage, changeLocale } from "./i18n";

afterEach(async () => {
  await i18n.changeLanguage("en");
  localStorage.clear();
});

describe("document language", () => {
  it("declares Portuguese once the interface switches to PT-BR", async () => {
    await changeLocale("pt-BR");

    expect(document.documentElement.lang).toBe("pt-BR");
  });

  it("declares English again when the user switches back", async () => {
    await changeLocale("pt-BR");
    await changeLocale("en");

    expect(document.documentElement.lang).toBe("en");
  });

  it("falls back to English for a locale outside the allowlist", async () => {
    await changeLocale("pt-BR");
    await changeLocale("de-DE");

    expect(document.documentElement.lang).toBe("en");
  });

  it("writes the attribute directly when asked", () => {
    applyDocumentLanguage("pt-BR");

    expect(document.documentElement.lang).toBe("pt-BR");
  });
});
