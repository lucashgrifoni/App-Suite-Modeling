import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusPill } from "./StatusPill";

describe("StatusPill", () => {
  it("renders its children", () => {
    render(<StatusPill>Active</StatusPill>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies the tone-specific classes", () => {
    const { rerender } = render(<StatusPill tone="danger">Down</StatusPill>);
    expect(screen.getByText("Down").className).toContain("text-red-950");
    rerender(<StatusPill tone="success">Up</StatusPill>);
    expect(screen.getByText("Up").className).toContain("text-emerald-950");
  });

  // Cada tom com cor tem de trazer tinta clara *e* escura: só a variante escura
  // (o estado anterior) perdia contraste sobre as superfícies claras.
  it.each([
    ["danger", "text-red-950", "dark:text-red-200"],
    ["success", "text-emerald-950", "dark:text-emerald-200"],
    ["warning", "text-amber-950", "dark:text-amber-200"],
    ["info", "text-sky-950", "dark:text-sky-200"],
  ] as const)("pairs light and dark ink for tone %s", (tone, light, dark) => {
    render(<StatusPill tone={tone}>{tone}</StatusPill>);
    const cls = screen.getByText(tone).className;
    expect(cls).toContain(light);
    expect(cls).toContain(dark);
  });

  it("keeps any extra className", () => {
    render(<StatusPill className="custom-x">Tag</StatusPill>);
    expect(screen.getByText("Tag").className).toContain("custom-x");
  });
});
