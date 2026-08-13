/**
 * Two screens that named a cause which could not apply.
 *
 * - The threats panel said "No threats match the filters." for a model that produced no
 *   threats at all, with the minimum score at its default 0 and no framework chosen —
 *   pointing the user at filters they never touched while the real cause was an incomplete
 *   model. The same string is correct when a filter really did hide everything, so only the
 *   nothing-to-filter case changes.
 * - The import page kept a file selected after the artifact type changed, submitted it, and
 *   then blamed the file: "The artifact could not be read as YAML or JSON. Check the file
 *   opens in an editor without syntax errors" — for a Terraform file that had parsed
 *   correctly seconds earlier under the Terraform type.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ImportPage } from "./ImportPage";
import { ThreatsAnalysisCard } from "../components/analysis/ThreatsAnalysisCard";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import type { HeuristicThreat } from "../types/api";

const importArtifact = vi.fn();
vi.mock("../api/otmApi", () => ({
  importArtifact: (...args: unknown[]) => importArtifact(...args),
}));

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter>
      <ToastProvider>
        <SessionProvider>{children}</SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

const THREAT = {
  id: "t1",
  title: "[spoofing] API",
  stride: "spoofing",
  target_component_id: "api",
  risk: { score: 12 },
} as unknown as HeuristicThreat;

function renderThreats(filtered: HeuristicThreat[], activeThreatCount: number) {
  render(
    <ThreatsAnalysisCard
      filtered={filtered}
      activeThreatCount={activeThreatCount}
      minScore={0}
      onMinScoreChange={() => {}}
      frameworkFilter=""
      onFrameworkFilterChange={() => {}}
      frameworks={[]}
    />,
    { wrapper: Providers },
  );
}

describe("the threats panel with nothing to show", () => {
  it("does not blame the filters when the analysis produced no threats", () => {
    renderThreats([], 0);

    expect(screen.queryByText(/No threats match the filters/)).toBeNull();
  });

  it("names the real cause and the next step", () => {
    renderThreats([], 0);

    expect(screen.getByText(/produced no threats for this model/)).toBeInTheDocument();
  });

  it("still blames the filters when a filter really did hide everything", () => {
    renderThreats([], 18);

    expect(screen.getByText(/No threats match the filters/)).toBeInTheDocument();
  });

  it("shows the rows when there are any", () => {
    renderThreats([THREAT], 1);

    expect(screen.getByText("[spoofing] API")).toBeInTheDocument();
  });
});

async function chooseTerraformFile(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText(/Artifact type/i), "terraform");
  const input = document.querySelector<HTMLInputElement>("#file")!;
  await user.upload(input, new File(['resource "aws_s3_bucket" "b" {}\n'], "main2.tf"));
}

beforeEach(() => {
  sessionStorage.clear();
  importArtifact.mockReset();
});

describe("changing the artifact type with a file already chosen", () => {
  it("drops a selection the new type does not accept", async () => {
    const user = userEvent.setup();
    render(<ImportPage />, { wrapper: Providers });
    await chooseTerraformFile(user);

    await user.selectOptions(screen.getByLabelText(/Artifact type/i), "openapi");

    expect(screen.queryByText("main2.tf")).toBeNull();
  });

  it("says why the selection went, instead of leaving it to be discovered", async () => {
    const user = userEvent.setup();
    render(<ImportPage />, { wrapper: Providers });
    await chooseTerraformFile(user);

    await user.selectOptions(screen.getByLabelText(/Artifact type/i), "openapi");

    expect(await screen.findByText(/is not one of the types this artifact accepts/)).toBeInTheDocument();
  });

  it("never submits the mismatched file, so no error blames it", async () => {
    const user = userEvent.setup();
    render(<ImportPage />, { wrapper: Providers });
    await chooseTerraformFile(user);
    await user.selectOptions(screen.getByLabelText(/Artifact type/i), "openapi");

    await user.click(screen.getByRole("button", { name: /Generate draft/i }));

    expect(importArtifact).not.toHaveBeenCalled();
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((a) => /Choose a file/.test(a.textContent ?? ""))).toBe(true);
  });

  it("keeps a file both types accept", async () => {
    const user = userEvent.setup();
    render(<ImportPage />, { wrapper: Providers });
    const input = document.querySelector<HTMLInputElement>("#file")!;
    await user.upload(input, new File(["openapi: 3.0.0\n"], "api.yaml"));

    await user.selectOptions(screen.getByLabelText(/Artifact type/i), "kubernetes");

    expect(screen.getByText("api.yaml")).toBeInTheDocument();
  });

  it("still imports the file under the type it matches", async () => {
    importArtifact.mockResolvedValue({ document: {}, inferences: [], unknowns: [] });
    const user = userEvent.setup();
    render(<ImportPage />, { wrapper: Providers });
    await chooseTerraformFile(user);

    await user.click(screen.getByRole("button", { name: /Generate draft/i }));

    await waitFor(() => expect(importArtifact).toHaveBeenCalledTimes(1));
  });
});
