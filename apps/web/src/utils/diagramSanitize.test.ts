import { describe, expect, it } from "vitest";
import { sanitizeDiagramLabel } from "./diagramSanitize";

describe("sanitizeDiagramLabel", () => {
  it("strips HTML tags", () => {
    expect(sanitizeDiagramLabel('<img src=x onerror="alert(1)">User')).toBe("User");
    expect(sanitizeDiagramLabel("A <b>B</b> C")).toBe("A B C");
  });

  it("normalizes whitespace and trims", () => {
    expect(sanitizeDiagramLabel("  foo   bar  ")).toBe("foo bar");
  });

  it("truncates to maxLen with ellipsis", () => {
    const long = "a".repeat(100);
    expect(sanitizeDiagramLabel(long, 10).length).toBe(10);
    expect(sanitizeDiagramLabel(long, 10).endsWith("…")).toBe(true);
  });

  it("does not truncate when within maxLen", () => {
    expect(sanitizeDiagramLabel("short", 120)).toBe("short");
  });

  it("strips greedily across a nested '<', as the previous regex did", () => {
    // `<[^>]*>` ran from the first `<` to the first `>`, swallowing any `<` between
    // them. Keep that: it is the safer reading of a malformed tag.
    expect(sanitizeDiagramLabel("<a<b>Users")).toBe("Users");
    expect(sanitizeDiagramLabel("<div onclick='<x'>Payments")).toBe("Payments");
  });

  it("keeps an unterminated '<' verbatim", () => {
    expect(sanitizeDiagramLabel("a < b")).toBe("a < b");
    expect(sanitizeDiagramLabel("Queue <worker")).toBe("Queue <worker");
    expect(sanitizeDiagramLabel("<b>Queue</b> <worker")).toBe("Queue <worker");
  });

  it("strips an empty tag", () => {
    expect(sanitizeDiagramLabel("A<>B")).toBe("AB");
  });

  it("stays linear on a pathological label (ReDoS regression)", () => {
    // A component name a user can paste into the wizard. With the old `/<[^>]*>/g`
    // this was ~950 ms at 64k characters and grew quadratically, because the engine
    // rescanned to the end of the input from every `<`. The length cap is applied
    // only after stripping, so nothing upstream bounded it.
    const pathological = "<".repeat(200_000);
    const started = performance.now();
    const out = sanitizeDiagramLabel(pathological);
    const elapsed = performance.now() - started;
    expect(out).toBe("<".repeat(119) + "…");
    expect(elapsed).toBeLessThan(1000);
  });
});
