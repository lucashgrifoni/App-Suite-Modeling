/**
 * `template_semantic_profile` is free text the user types in the wizard, and its value is
 * used as an object key. `BY_PROFILE["constructor"]` returned `Object`, whose `.length` is
 * 1, which cleared the wizard's `adaptivePrompts.length > 0` guard and then threw
 * `adaptivePrompts.map is not a function` during render — into an ErrorBoundary whose only
 * recovery reloads the same poisoned document out of sessionStorage.
 */
import { describe, expect, it } from "vitest";
import { promptsForProfile } from "./adaptiveWizard";

describe("promptsForProfile", () => {
  it("returns the prompts declared for a known profile", () => {
    const prompts = promptsForProfile("api_backend_rest");
    expect(prompts.length).toBeGreaterThan(0);
    expect(prompts.map((p) => p.id)).toContain("auth");
  });

  it("normalises case and surrounding whitespace, as the wizard does", () => {
    expect(promptsForProfile("  API_Backend_REST ")).toEqual(promptsForProfile("api_backend_rest"));
  });

  it.each([
    "constructor",
    "__proto__",
    "prototype",
    "tostring",
    "valueof",
    "hasownproperty",
    "unknown_profile",
    "",
    "   ",
  ])("is total over arbitrary user text: %j", (profile) => {
    const prompts = promptsForProfile(profile);
    expect(Array.isArray(prompts)).toBe(true);
    // The render path is `.length > 0` then `.map`; both must be safe on the result.
    expect(() => prompts.map((p) => p.id)).not.toThrow();
  });

  it("reports no prompts for a profile it does not know, rather than inherited members", () => {
    expect(promptsForProfile("constructor")).toEqual([]);
    expect(promptsForProfile("unknown_profile")).toEqual([]);
  });

  it("returns nothing when no profile is set", () => {
    expect(promptsForProfile(undefined)).toEqual([]);
  });
});
