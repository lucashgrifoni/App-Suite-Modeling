import createDOMPurify from "dompurify";
import { jsPDF } from "jspdf";
import { afterEach, describe, expect, it } from "vitest";

afterEach(() => {
  document.body.replaceChildren();
});

describe("PDF dependency security regressions", () => {
  it.each(["afterSanitizeElements", "afterSanitizeAttributes"] as const)(
    "neutralizes descendants detached by %s in IN_PLACE mode (GHSA-p98j-92pf-mc4p)",
    (hook) => {
      const purify = createDOMPurify(window);
      const root = document.createElement("div");
      root.innerHTML = '<section id="wrap"><img src="x" onerror="ATTACKER()"></section>';
      document.body.appendChild(root);
      const image = root.querySelector("img")!;
      const removeWrapper = (node: Node) => {
        if (!(node instanceof Element)) return;
        if (node.id === "wrap") node.remove();
      };
      if (hook === "afterSanitizeElements") purify.addHook(hook, removeWrapper);
      else purify.addHook(hook, removeWrapper);

      purify.sanitize(root, { IN_PLACE: true });

      expect(image.hasAttribute("onerror")).toBe(false);
    },
  );

  it("does not return executable markup from a removed rawtext root (GHSA-6688-9rhm-gjv2)", () => {
    const purify = createDOMPurify(window);
    const root = document.createElement("style");
    root.textContent = "</style><img src=x onerror=1>";
    document.body.appendChild(root);
    let serialized = "";
    try {
      const returned = purify.sanitize(root, { IN_PLACE: true });
      if (returned instanceof Element) serialized = returned.outerHTML;
    } catch (error) {
      expect(error).toBeInstanceOf(TypeError);
    }
    const probe = document.createElement("div");
    probe.innerHTML = serialized;

    expect(probe.querySelector("img[onerror]")).toBeNull();
  });

  it("preserves ordinary sanitization and the text-only PDF export path", () => {
    const purify = createDOMPurify(window);
    expect(purify.sanitize('<p>Hello <strong>world</strong><img src=x onerror=1></p>')).toBe(
      '<p>Hello <strong>world</strong><img src="x"></p>',
    );
    const pdf = new jsPDF({ unit: "mm", format: "a4" });
    pdf.text("Threat model report", 16, 18);
    expect(pdf.output()).toContain("%PDF-");
    expect(pdf.output()).toContain("Threat model report");
  });
});
