/**
 * The import review — the list the product tells the user to read before running the
 * engine — lived in component state while the draft it describes lived in sessionStorage.
 * A refresh left the draft in place and the review gone, with no message and no way back.
 *
 * The pairing is the delicate half: a review is a statement about one exact draft, so
 * showing it beside a different model would be a worse failure than showing nothing.
 */

import { describe, expect, it } from "vitest";
import {
  clearImportReview,
  readImportReview,
  saveImportReview,
  type ImportReview,
} from "./importReviewStorage";
import type { ArtifactInference } from "../types/api";

const INFERENCES = [
  {
    id: "api_surface",
    confidence: "high",
    message: "Superfície de API e 3 operação(ões) HTTP inferida(s) a partir de `paths`.",
  },
] as unknown as ArtifactInference[];

function review(documentKey = "abcd1234"): ImportReview {
  return {
    documentKey,
    inferences: INFERENCES,
    unknowns: ["Classificação de dados requer revisão manual."],
    explanations: null,
  };
}

describe("importReviewStorage", () => {
  it("returns the review for the document it was computed from", () => {
    saveImportReview(review());
    expect(readImportReview("abcd1234")?.inferences).toHaveLength(1);
  });

  it("keeps the not-inferred list too", () => {
    saveImportReview(review());
    expect(readImportReview("abcd1234")?.unknowns).toEqual([
      "Classificação de dados requer revisão manual.",
    ]);
  });

  it("keeps the structured explanations when the import produced them", () => {
    const explanations = [{ id: "e1", kind: "inference" }] as unknown as ImportReview["explanations"];
    saveImportReview({ ...review(), explanations });
    expect(readImportReview("abcd1234")?.explanations).toEqual(explanations);
  });

  it("withholds a review that describes a different document", () => {
    saveImportReview(review("abcd1234"));
    expect(readImportReview("ffff0000")).toBeNull();
  });

  it("returns nothing when there is no session document to match against", () => {
    saveImportReview(review());
    expect(readImportReview(null)).toBeNull();
  });

  it("returns nothing when nothing was stored", () => {
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("forgets the review on request", () => {
    saveImportReview(review());
    clearImportReview();
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("ignores a stored value that is not JSON", () => {
    sessionStorage.setItem("otm.web.import.review", "{not json");
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("ignores a stored value that is not a review", () => {
    sessionStorage.setItem("otm.web.import.review", JSON.stringify({ documentKey: "abcd1234" }));
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("ignores a review whose inference list is not a list of records", () => {
    const bad = { ...review(), inferences: ["just a string"] };
    sessionStorage.setItem("otm.web.import.review", JSON.stringify(bad));
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("ignores a review whose unknowns are not strings", () => {
    const bad = { ...review(), unknowns: [{ text: "no" }] };
    sessionStorage.setItem("otm.web.import.review", JSON.stringify(bad));
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("ignores a review whose explanations are neither null nor records", () => {
    const bad = { ...review(), explanations: "nope" };
    sessionStorage.setItem("otm.web.import.review", JSON.stringify(bad));
    expect(readImportReview("abcd1234")).toBeNull();
  });

  it("ignores a review with an empty fingerprint, which would match nothing meaningful", () => {
    sessionStorage.setItem("otm.web.import.review", JSON.stringify(review("")));
    expect(readImportReview("")).toBeNull();
  });

  it("accepts an empty review, which is what a clean artifact legitimately produces", () => {
    saveImportReview({ documentKey: "abcd1234", inferences: [], unknowns: [], explanations: null });
    expect(readImportReview("abcd1234")).toEqual({
      documentKey: "abcd1234",
      inferences: [],
      unknowns: [],
      explanations: null,
    });
  });
});
