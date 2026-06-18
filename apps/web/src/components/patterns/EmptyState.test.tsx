import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders the title as a heading and the description", () => {
    render(<EmptyState title="Nothing here yet" description="Create your first model" />);
    expect(screen.getByRole("heading", { name: "Nothing here yet" })).toBeInTheDocument();
    expect(screen.getByText("Create your first model")).toBeInTheDocument();
  });

  it("renders an action when provided", () => {
    render(<EmptyState title="t" action={<button type="button">Get started</button>} />);
    expect(screen.getByRole("button", { name: "Get started" })).toBeInTheDocument();
  });

  it("omits the description when not provided", () => {
    render(<EmptyState title="Only a title" />);
    expect(screen.getByRole("heading", { name: "Only a title" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
