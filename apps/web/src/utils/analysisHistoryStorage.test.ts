import { describe, expect, it } from "vitest";
import type { AnalysisHistoryEntry } from "../types/analysisHistory";
import { loadHistory, pushHistoryEntry, saveHistory } from "./analysisHistoryStorage";

const KEY = "otm.analysis.history";

function entry(id: string, over: Partial<AnalysisHistoryEntry> = {}): AnalysisHistoryEntry {
  return {
    id,
    createdAt: 1,
    trigger: "analysis",
    title: "T",
    systemType: "web_application",
    maxScore: null,
    summaryLine: "s",
    document: { model: { schema_version: "1.0.0" }, metadata: { title: "T" } },
    analysis: null,
    ...over,
  } as AnalysisHistoryEntry;
}

describe("analysisHistoryStorage", () => {
  it("round-trips valid entries", () => {
    saveHistory([entry("a"), entry("b")]);
    expect(loadHistory().map((e) => e.id)).toEqual(["a", "b"]);
  });

  it("returns [] for malformed JSON or a non-array payload", () => {
    localStorage.setItem(KEY, "{ not json");
    expect(loadHistory()).toEqual([]);
    localStorage.setItem(KEY, JSON.stringify({ not: "an array" }));
    expect(loadHistory()).toEqual([]);
  });

  it("drops entries that fail validation (bad trigger / missing model or metadata)", () => {
    localStorage.setItem(
      KEY,
      JSON.stringify([
        entry("ok"),
        { id: "bad-trigger", createdAt: 1, trigger: "nope", document: { model: {}, metadata: {} } },
        { id: "no-metadata", createdAt: 1, trigger: "analysis", document: { model: {} } },
        { id: "no-createdAt", trigger: "analysis", document: { model: {}, metadata: {} } },
      ]),
    );
    expect(loadHistory().map((e) => e.id)).toEqual(["ok"]);
  });

  it("prepends, de-duplicates by id, and caps at 20 entries", () => {
    for (let i = 0; i < 25; i += 1) pushHistoryEntry(entry(`e${i}`));
    const ids = loadHistory().map((e) => e.id);
    expect(ids).toHaveLength(20);
    expect(ids[0]).toBe("e24"); // most recent first

    pushHistoryEntry(entry("e24"));
    expect(loadHistory().filter((e) => e.id === "e24")).toHaveLength(1);
  });
});
