import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskScoreBar } from "./RiskScoreBar";

function fill(): HTMLElement {
  return screen.getByRole("progressbar").firstElementChild as HTMLElement;
}

describe("RiskScoreBar", () => {
  it("renders a progressbar with the right aria values and proportional width", () => {
    render(<RiskScoreBar score={10} maxScore={20} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "10");
    expect(bar).toHaveAttribute("aria-valuemax", "20");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(fill().style.width).toBe("50%");
  });

  it("clamps a score above the max to 100%", () => {
    render(<RiskScoreBar score={50} maxScore={25} />);
    expect(fill().style.width).toBe("100%");
  });

  it("treats a null score as 0", () => {
    render(<RiskScoreBar score={null} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
    expect(fill().style.width).toBe("0%");
  });

  it("hides the footer in the compact variant", () => {
    const { container } = render(<RiskScoreBar score={5} variant="compact" />);
    expect(container.querySelector("p")).toBeNull();
  });
});
