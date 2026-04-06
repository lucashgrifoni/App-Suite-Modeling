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
});
