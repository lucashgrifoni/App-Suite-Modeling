import { describe, expect, it, vi } from "vitest";
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
    document: { model: { schema_version: "1.0.0" }, metadata: { title: "T" } },
    analysis: null,
    ...over,
  } as AnalysisHistoryEntry;
}

/** An entry whose serialized size is dominated by a predictable payload. */
function bigEntry(id: string, payloadChars: number): AnalysisHistoryEntry {
  return entry(id, {
    document: {
      model: { schema_version: "1.0.0" },
      metadata: { title: "T", summary: "x".repeat(payloadChars) },
    },
  } as Partial<AnalysisHistoryEntry>);
}

/**
 * localStorage with a hard byte ceiling, which jsdom's implementation does not have.
 *
 * A real browser answers an over-quota `setItem` with a thrown QuotaExceededError and
 * leaves the previous value in place — exactly the condition that used to freeze the
 * history list.
 */
function installQuotaLimitedStorage(maxChars: number): void {
  const backing = new Map<string, string>();
  vi.spyOn(Storage.prototype, "getItem").mockImplementation((k: string) => backing.get(k) ?? null);
  vi.spyOn(Storage.prototype, "removeItem").mockImplementation((k: string) => {
    backing.delete(k);
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation((k: string, v: string) => {
    if (v.length > maxChars) {
      const err = new Error("The quota has been exceeded.");
      err.name = "QuotaExceededError";
      throw err;
    }
    backing.set(k, v);
  });
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

/**
 * Persistence used to stop dead the first time the origin quota was exhausted: `saveHistory`
 * swallowed the QuotaExceededError, so the stored list froze at whatever fitted first and
 * every subsequent snapshot vanished while the UI still announced success. It was the
 * newest work that was thrown away — the oldest entries were the ones that survived.
 */
describe("analysisHistoryStorage under an exhausted quota", () => {
  it("keeps the newest snapshot instead of freezing on the oldest ones", () => {
    installQuotaLimitedStorage(900);
    for (let i = 0; i < 10; i += 1) pushHistoryEntry(bigEntry(`e${i}`, 200));

    expect(loadHistory()[0]?.id).toBe("e9");
  });

  it("sheds the oldest entries to make room rather than dropping the write", () => {
    installQuotaLimitedStorage(900);
    for (let i = 0; i < 10; i += 1) pushHistoryEntry(bigEntry(`e${i}`, 200));

    expect(loadHistory().some((e) => e.id === "e0")).toBe(false);
  });

  it("still stores something rather than nothing", () => {
    installQuotaLimitedStorage(900);
    for (let i = 0; i < 10; i += 1) pushHistoryEntry(bigEntry(`e${i}`, 200));

    expect(loadHistory().length).toBeGreaterThan(0);
  });

  it("reports that older entries were evicted", () => {
    installQuotaLimitedStorage(900);
    for (let i = 0; i < 9; i += 1) pushHistoryEntry(bigEntry(`e${i}`, 200));

    expect(pushHistoryEntry(bigEntry("newest", 200))).toBe("evicted");
  });

  it("reports a clean write when everything fits", () => {
    installQuotaLimitedStorage(100_000);

    expect(pushHistoryEntry(entry("a"))).toBe("ok");
  });

  it("reports failure when not even one entry fits", () => {
    installQuotaLimitedStorage(10);

    expect(pushHistoryEntry(bigEntry("huge", 500))).toBe("failed");
  });

  it("treats storing an empty list as a successful write", () => {
    installQuotaLimitedStorage(10);

    expect(saveHistory([])).toBe("ok");
  });

  it("clears the stored list when the caller deliberately saves an empty one", () => {
    installQuotaLimitedStorage(100_000);
    pushHistoryEntry(entry("a"));

    saveHistory([]);

    expect(loadHistory()).toEqual([]);
  });
});

/**
 * The shrink loop above used to end by REMOVING the key when even the newest entry alone
 * was over quota, which turned "this one snapshot did not fit" into "your whole history is
 * gone". A rejected `setItem` leaves the previous value intact in every browser, so the
 * stored list was still perfectly valid and still fitted; deleting it destroyed entries the
 * user had already earned in order to report a failure the UI announces anyway via
 * `history.toastStorageFull`. Losing the new snapshot is the acceptable half of this trade.
 */
describe("analysisHistoryStorage when not even the newest entry fits", () => {
  it("keeps the entries that were already stored", () => {
    installQuotaLimitedStorage(2000);
    pushHistoryEntry(entry("a"));
    pushHistoryEntry(entry("b"));
    pushHistoryEntry(entry("c"));

    pushHistoryEntry(bigEntry("huge", 5000));

    expect(loadHistory().map((e) => e.id)).toEqual(["c", "b", "a"]);
  });

  it("still reports the failure so the caller can warn", () => {
    installQuotaLimitedStorage(2000);
    pushHistoryEntry(entry("a"));

    expect(pushHistoryEntry(bigEntry("huge", 5000))).toBe("failed");
  });

  it("does not store the oversized snapshot itself", () => {
    installQuotaLimitedStorage(2000);
    pushHistoryEntry(entry("a"));

    pushHistoryEntry(bigEntry("huge", 5000));

    expect(loadHistory().some((e) => e.id === "huge")).toBe(false);
  });
});
