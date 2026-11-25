import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskScoreBar } from "./RiskScoreBar";

function bar(): HTMLProgressElement {
  return screen.getByRole("progressbar") as HTMLProgressElement;
}

function fill(): HTMLElement {
  return screen.getByTestId("risk-score-track").firstElementChild as HTMLElement;
}

describe("RiskScoreBar", () => {
  it("renders a progressbar with the right values and proportional width", () => {
    render(<RiskScoreBar score={10} maxScore={20} />);
    expect(bar().value).toBe(10);
    expect(bar().max).toBe(20);
    expect(bar()).toHaveAccessibleName();
    expect(fill().style.width).toBe("50%");
  });

  it("clamps a score above the max to 100%", () => {
    render(<RiskScoreBar score={50} maxScore={25} />);
    expect(fill().style.width).toBe("100%");
    // The announced value must not exceed the announced maximum.
    expect(bar().value).toBe(25);
    expect(bar().max).toBe(25);
  });

  it("treats a null score as 0", () => {
    render(<RiskScoreBar score={null} />);
    expect(bar().value).toBe(0);
    expect(fill().style.width).toBe("0%");
  });

  it("keeps the decorative bar out of the accessibility tree", () => {
    render(<RiskScoreBar score={5} />);
    // Exactly one progressbar: the native element, not the styled div.
    expect(screen.getAllByRole("progressbar")).toHaveLength(1);
    expect(screen.getByTestId("risk-score-track")).toHaveAttribute("aria-hidden", "true");
  });

  it("hides the footer in the compact variant", () => {
    const { container } = render(<RiskScoreBar score={5} variant="compact" />);
    expect(container.querySelector("p")).toBeNull();
  });
});
