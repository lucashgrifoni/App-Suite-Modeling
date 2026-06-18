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
    expect(screen.getByText("Down").className).toContain("text-red-200");
    rerender(<StatusPill tone="success">Up</StatusPill>);
    expect(screen.getByText("Up").className).toContain("text-emerald-200");
  });

  it("keeps any extra className", () => {
    render(<StatusPill className="custom-x">Tag</StatusPill>);
    expect(screen.getByText("Tag").className).toContain("custom-x");
  });
});
